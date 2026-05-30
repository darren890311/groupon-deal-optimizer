package server

import (
	"context"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"

	"github.com/darren890311/groupon-deal-optimizer/api/internal/worker"
)

// fakeCache is an in-memory Cache for handler tests.
type fakeCache struct {
	getRaw    json.RawMessage
	getHit    bool
	putCalled bool
}

func (f *fakeCache) Get(context.Context, string) (json.RawMessage, bool, error) {
	return f.getRaw, f.getHit, nil
}
func (f *fakeCache) Put(context.Context, string, json.RawMessage, time.Duration) error {
	f.putCalled = true
	return nil
}
func (f *fakeCache) Ping(context.Context) error { return nil }

func testRouter(cache *fakeCache, workerURL string) *gin.Engine {
	gin.SetMode(gin.TestMode)
	s := New(cache, worker.New(workerURL), time.Hour, slog.New(slog.NewTextHandler(io.Discard, nil)))
	return s.Router("*")
}

func postAnalyze(router *gin.Engine, body string) *httptest.ResponseRecorder {
	w := httptest.NewRecorder()
	req, _ := http.NewRequest(http.MethodPost, "/analyze", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)
	return w
}

func TestAnalyze_CacheHit_SkipsWorker(t *testing.T) {
	cache := &fakeCache{getRaw: json.RawMessage(`{"cached":true}`), getHit: true}
	ws := httptest.NewServer(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {
		t.Error("worker must not be called on a cache hit")
	}))
	defer ws.Close()

	w := postAnalyze(testRouter(cache, ws.URL), `{"url":"https://www.groupon.com/deals/x"}`)

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", w.Code)
	}
	if got := w.Header().Get("X-Cache"); got != "HIT" {
		t.Errorf("X-Cache = %q, want HIT", got)
	}
	if w.Body.String() != `{"cached":true}` {
		t.Errorf("body = %q", w.Body.String())
	}
}

func TestAnalyze_CacheMiss_CallsWorkerAndStores(t *testing.T) {
	cache := &fakeCache{getHit: false}
	ws := httptest.NewServer(http.HandlerFunc(func(rw http.ResponseWriter, _ *http.Request) {
		rw.Header().Set("Content-Type", "application/json")
		_, _ = rw.Write([]byte(`{"fresh":true}`))
	}))
	defer ws.Close()

	w := postAnalyze(testRouter(cache, ws.URL), `{"url":"https://www.groupon.com/deals/x"}`)

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", w.Code)
	}
	if got := w.Header().Get("X-Cache"); got != "MISS" {
		t.Errorf("X-Cache = %q, want MISS", got)
	}
	if !cache.putCalled {
		t.Error("expected Put to be called on a cache miss")
	}
	if w.Body.String() != `{"fresh":true}` {
		t.Errorf("body = %q", w.Body.String())
	}
}

func TestAnalyze_RejectsNonGrouponURL(t *testing.T) {
	w := postAnalyze(testRouter(&fakeCache{}, "http://unused"), `{"url":"https://example.com/foo"}`)
	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("status = %d, want 422", w.Code)
	}
}

func TestAnalyze_RejectsMissingURL(t *testing.T) {
	w := postAnalyze(testRouter(&fakeCache{}, "http://unused"), `{}`)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", w.Code)
	}
}
