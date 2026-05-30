// Package store is the Postgres-backed analysis cache.
package store

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// Cache is the persistence the server depends on. An interface so handlers can
// be tested against a fake without a real database.
type Cache interface {
	Get(ctx context.Context, url string) (result json.RawMessage, hit bool, err error)
	Put(ctx context.Context, url string, result json.RawMessage, ttl time.Duration) error
	Ping(ctx context.Context) error
}

// Postgres implements Cache over a pgx connection pool.
type Postgres struct {
	pool *pgxpool.Pool
}

func New(ctx context.Context, dsn string) (*Postgres, error) {
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		return nil, err
	}
	return &Postgres{pool: pool}, nil
}

func (p *Postgres) Migrate(ctx context.Context) error {
	_, err := p.pool.Exec(ctx, `
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

// Get returns the cached result if it exists and has not expired.
func (p *Postgres) Get(ctx context.Context, url string) (json.RawMessage, bool, error) {
	var raw json.RawMessage
	err := p.pool.QueryRow(ctx,
		`SELECT result_json FROM analyses WHERE url=$1 AND expires_at > now()`, url,
	).Scan(&raw)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, false, nil
	}
	if err != nil {
		return nil, false, err
	}
	return raw, true, nil
}

func (p *Postgres) Put(ctx context.Context, url string, result json.RawMessage, ttl time.Duration) error {
	_, err := p.pool.Exec(ctx, `
		INSERT INTO analyses (url, result_json, analyzed_at, expires_at)
		VALUES ($1, $2, now(), $3)
		ON CONFLICT (url) DO UPDATE
		   SET result_json = EXCLUDED.result_json,
		       analyzed_at = now(),
		       expires_at  = EXCLUDED.expires_at
	`, url, result, time.Now().Add(ttl))
	return err
}

func (p *Postgres) Ping(ctx context.Context) error { return p.pool.Ping(ctx) }

func (p *Postgres) Close() { p.pool.Close() }
