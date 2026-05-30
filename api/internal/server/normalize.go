package server

import (
	"net/url"
	"strings"
)

// normalizeURL drops the query/fragment (e.g. ?redemptionLocationId=...) and any
// trailing slash so the same deal maps to one cache key. Mirrors the worker's
// scrape.normalize_url.
func normalizeURL(raw string) string {
	u, err := url.Parse(raw)
	if err != nil {
		return raw
	}
	return strings.TrimRight(u.Scheme+"://"+u.Host+u.Path, "/")
}
