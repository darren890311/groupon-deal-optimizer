// Package worker is an HTTP client for the Python analysis worker.
package worker

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"strings"
)

type Client struct {
	baseURL string
	http    *http.Client
}

func New(baseURL string) *Client {
	return &Client{baseURL: strings.TrimRight(baseURL, "/"), http: &http.Client{}}
}

// Analyze posts the deal URL to the worker and returns the raw response body and
// status code. The caller owns the deadline via ctx (the worker can take ~12s).
func (c *Client) Analyze(ctx context.Context, dealURL string) ([]byte, int, error) {
	body, _ := json.Marshal(map[string]string{"url": dealURL})
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
