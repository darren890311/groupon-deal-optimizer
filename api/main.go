// Command api is the stateful gateway in front of the Python analyzer worker.
//
// Flow: receive a Groupon deal URL → look it up in Postgres (keyed by the
// normalized URL) → return the cached DealAnalysis if still fresh → otherwise
// call the worker, persist the result, and return it. The worker stays
// stateless; this layer owns caching + history.
package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/darren890311/revelio/api/internal/config"
	"github.com/darren890311/revelio/api/internal/server"
	"github.com/darren890311/revelio/api/internal/store"
	"github.com/darren890311/revelio/api/internal/worker"
)

func main() {
	log := slog.New(slog.NewJSONHandler(os.Stdout, nil))

	cfg, err := config.Load()
	if err != nil {
		log.Error("config", "err", err)
		os.Exit(1)
	}

	ctx := context.Background()
	db, err := store.New(ctx, cfg.DatabaseURL)
	if err != nil {
		log.Error("db connect", "err", err)
		os.Exit(1)
	}
	defer db.Close()
	if err := db.Migrate(ctx); err != nil {
		log.Error("migrate", "err", err)
		os.Exit(1)
	}

	srv := server.New(db, worker.New(cfg.WorkerURL), cfg.CacheTTL, log)
	httpServer := &http.Server{
		Addr:    ":" + cfg.Port,
		Handler: srv.Router(cfg.AllowedOrigin),
	}

	// Run until SIGINT/SIGTERM, then drain in-flight requests gracefully.
	rootCtx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	go func() {
		log.Info("api listening", "port", cfg.Port, "worker", cfg.WorkerURL)
		if err := httpServer.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Error("server", "err", err)
			stop()
		}
	}()

	<-rootCtx.Done()
	log.Info("shutting down")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := httpServer.Shutdown(shutdownCtx); err != nil {
		log.Error("shutdown", "err", err)
	}
}
