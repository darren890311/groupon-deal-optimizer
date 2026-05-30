// Command api is the stateful gateway in front of the Python analyzer worker.
//
// Flow: receive a Groupon deal URL → look it up in Postgres (keyed by the
// normalized URL) → return the cached DealAnalysis if it is still fresh →
// otherwise call the worker, persist the result, and return it.
//
// The worker stays stateless; this layer owns caching + history.
package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

const cacheTTL = 24 * time.Hour

type analyzeRequest struct {
	URL string `json:"url"`
}

type server struct {
	db        *pgxpool.Pool
	workerURL string
	http      *http.Client
}

func main() {
	ctx := context.Background()

	pool, err := pgxpool.New(ctx, mustEnv("DATABASE_URL"))
	if err != nil {
		log.Fatalf("db connect: %v", err)
	}
	defer pool.Close()
	if err := migrate(ctx, pool); err != nil {
		log.Fatalf("migrate: %v", err)
	}

	s := &server{
		db:        pool,
		workerURL: strings.TrimRight(envOr("WORKER_URL", "http://127.0.0.1:8000"), "/"),
		http:      &http.Client{Timeout: 120 * time.Second},
	}

	r := gin.Default()
	r.Use(corsMiddleware(envOr("ALLOWED_ORIGIN", "*")))
	r.GET("/healthz", s.healthz)
	r.POST("/analyze", s.analyze)

	port := envOr("PORT", "8080")
	log.Printf("api listening on :%s (worker=%s)", port, s.workerURL)
	if err := r.Run(":" + port); err != nil {
		log.Fatalf("server: %v", err)
	}
}

func migrate(ctx context.Context, db *pgxpool.Pool) error {
	_, err := db.Exec(ctx, `
		CREATE TABLE IF NOT EXISTS analyses (
			url         TEXT PRIMARY KEY,
			result_json JSONB NOT NULL,
			analyzed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
			expires_at  TIMESTAMPTZ NOT NULL
		);
		CREATE INDEX IF NOT EXISTS analyses_expires_at_idx ON analyses (expires_at);
	`)
	return err
}

func (s *server) healthz(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 2*time.Second)
	defer cancel()
	c.JSON(http.StatusOK, gin.H{"status": "ok", "db": s.db.Ping(ctx) == nil})
}

func (s *server) analyze(c *gin.Context) {
	var req analyzeRequest
	if err := c.ShouldBindJSON(&req); err != nil || strings.TrimSpace(req.URL) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "missing url"})
		return
	}
	if !strings.Contains(req.URL, "groupon.com/deals/") {
		c.JSON(http.StatusUnprocessableEntity, gin.H{"error": "not a Groupon deal URL (expected groupon.com/deals/<slug>)"})
		return
	}

	ctx := c.Request.Context()
	key := normalizeURL(req.URL)

	// Cache hit → serve the stored JSON straight through.
	var cached json.RawMessage
	err := s.db.QueryRow(ctx, `SELECT result_json FROM analyses WHERE url=$1 AND expires_at > now()`, key).Scan(&cached)
	if err == nil {
		c.Header("X-Cache", "HIT")
		c.Data(http.StatusOK, "application/json", cached)
		return
	}
	if !errors.Is(err, pgx.ErrNoRows) {
		log.Printf("cache lookup error: %v", err) // non-fatal: fall through to the worker
	}

	// Miss → ask the worker.
	body, _ := json.Marshal(analyzeRequest{URL: req.URL})
	resp, err := s.http.Post(s.workerURL+"/analyze", "application/json", bytes.NewReader(body))
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "worker unreachable: " + err.Error()})
		return
	}
	defer resp.Body.Close()
	raw, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK {
		c.Data(resp.StatusCode, "application/json", raw) // pass the worker's error through verbatim
		return
	}

	// Persist (upsert) then return.
	if _, err := s.db.Exec(ctx, `
		INSERT INTO analyses (url, result_json, analyzed_at, expires_at)
		VALUES ($1, $2, now(), $3)
		ON CONFLICT (url) DO UPDATE
		   SET result_json = EXCLUDED.result_json,
		       analyzed_at = now(),
		       expires_at  = EXCLUDED.expires_at
	`, key, raw, time.Now().Add(cacheTTL)); err != nil {
		log.Printf("cache store error: %v", err) // non-fatal: still return the fresh result
	}

	c.Header("X-Cache", "MISS")
	c.Data(http.StatusOK, "application/json", raw)
}

// normalizeURL drops the query/fragment (e.g. ?redemptionLocationId=...) and any
// trailing slash, so the same deal maps to one cache key. Mirrors the worker's
// scrape.normalize_url.
func normalizeURL(raw string) string {
	u, err := url.Parse(raw)
	if err != nil {
		return raw
	}
	return strings.TrimRight(u.Scheme+"://"+u.Host+u.Path, "/")
}

func corsMiddleware(allowed string) gin.HandlerFunc {
	cfg := cors.DefaultConfig()
	cfg.AllowMethods = []string{"GET", "POST"}
	cfg.AllowHeaders = []string{"Origin", "Content-Type"}
	if allowed == "*" {
		cfg.AllowAllOrigins = true
	} else {
		cfg.AllowOrigins = strings.Split(allowed, ",")
	}
	return cors.New(cfg)
}

func mustEnv(k string) string {
	v := os.Getenv(k)
	if v == "" {
		log.Fatalf("missing required env var %s", k)
	}
	return v
}

func envOr(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}
