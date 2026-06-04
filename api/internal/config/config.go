// Package config loads runtime configuration from the environment.
package config

import (
	"errors"
	"os"
	"time"
)

type Config struct {
	RedisURL      string
	WorkerURL     string
	Port          string
	AllowedOrigin string
	CacheTTL      time.Duration
}

// Load reads config from the environment, applying defaults. REDIS_URL is
// required; everything else has a sensible local-dev default.
func Load() (Config, error) {
	c := Config{
		RedisURL:      os.Getenv("REDIS_URL"),
		WorkerURL:     envOr("WORKER_URL", "http://127.0.0.1:8000"),
		Port:          envOr("PORT", "8080"),
		AllowedOrigin: envOr("ALLOWED_ORIGIN", "*"),
		CacheTTL:      24 * time.Hour,
	}
	if c.RedisURL == "" {
		return Config{}, errors.New("REDIS_URL is required")
	}
	return c, nil
}

func envOr(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}
