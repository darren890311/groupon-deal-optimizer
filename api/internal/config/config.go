// Package config loads runtime configuration from the environment.
package config

import (
	"errors"
	"os"
	"time"
)

type Config struct {
	DatabaseURL   string
	WorkerURL     string
	Port          string
	AllowedOrigin string
	CacheTTL      time.Duration
}

// Load reads config from the environment, applying defaults. DATABASE_URL is
// required; everything else has a sensible local-dev default.
func Load() (Config, error) {
	c := Config{
		DatabaseURL:   os.Getenv("DATABASE_URL"),
		WorkerURL:     envOr("WORKER_URL", "http://127.0.0.1:8000"),
		Port:          envOr("PORT", "8080"),
		AllowedOrigin: envOr("ALLOWED_ORIGIN", "*"),
		CacheTTL:      24 * time.Hour,
	}
	if c.DatabaseURL == "" {
		return Config{}, errors.New("DATABASE_URL is required")
	}
	return c, nil
}

func envOr(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}
