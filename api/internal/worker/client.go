// Package worker is an HTTP client for the Python analysis worker.
package worker

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"strings"

	"google.golang.org/api/idtoken"
)

type Client struct {
	baseURL string
	http    *http.Client
}

func New(baseURL string) *Client {
	base := strings.TrimRight(baseURL, "/")
	// Authenticated service-to-service calls: attach a Google-signed identity
	// token whose audience is the worker URL, so the worker can stay private.
	// On Cloud Run this uses the service account; locally (no ADC) we fall back
	// to an unauthenticated client, which is fine against a local/public worker.
	httpClient := http.DefaultClient
	if c, err := idtoken.NewClient(context.Background(), base); err == nil {
		httpClient = c
	} else {
		slog.Warn("idtoken client unavailable; calling worker unauthenticated", "err", err)
	}
	return &Client{baseURL: base, http: httpClient}
}

// Analyze posts the deal URL (and, when the extension supplies it, the rendered
// page HTML) to the worker and returns the raw response body and status code.
// An empty html falls back to the worker's own Playwright fetch. The caller owns
// the deadline via ctx.
func (c *Client) Analyze(ctx context.Context, dealURL, html string) ([]byte, int, error) {
	body, _ := json.Marshal(struct {
		URL  string `json:"url"`
		HTML string `json:"html,omitempty"`
	}{URL: dealURL, HTML: html})
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/analyze", bytes.NewReader(body))
	if err != nil {
		return nil, 0, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.http.Do(req)
	if err != nil {
		return nil, 0, err
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(resp.Body)
	return raw, resp.StatusCode, err
}
