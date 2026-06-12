// Package store is the Redis-backed analysis cache.
package store

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	"github.com/redis/go-redis/v9"
)

// Cache is the persistence the server depends on. An interface so handlers can
// be tested against a fake without a real datastore.
type Cache interface {
	Get(ctx context.Context, url string) (result json.RawMessage, hit bool, err error)
	Put(ctx context.Context, url string, result json.RawMessage, ttl time.Duration) error
	Ping(ctx context.Context) error
}

// keyPrefix namespaces our keys so the cache can share a Redis instance.
const keyPrefix = "analysis:"

// Redis implements Cache over a go-redis client. Each analysis is a single key
// with a native TTL, so expiry is handled by Redis itself - no cleanup job.
type Redis struct {
	client *redis.Client
}

// New connects to Redis from a connection URL (rediss:// enables TLS, which
// Upstash requires) and verifies the connection.
func New(ctx context.Context, url string) (*Redis, error) {
	opt, err := redis.ParseURL(url)
	if err != nil {
		return nil, err
	}
	client := redis.NewClient(opt)
	if err := client.Ping(ctx).Err(); err != nil {
		return nil, err
	}
	return &Redis{client: client}, nil
}

// Get returns the cached result if the key exists and has not expired.
func (r *Redis) Get(ctx context.Context, url string) (json.RawMessage, bool, error) {
	val, err := r.client.Get(ctx, keyPrefix+url).Bytes()
	if errors.Is(err, redis.Nil) {
		return nil, false, nil
	}
	if err != nil {
		return nil, false, err
	}
	return json.RawMessage(val), true, nil
}

// Put stores the result under the URL key with a TTL. Re-analysis overwrites.
func (r *Redis) Put(ctx context.Context, url string, result json.RawMessage, ttl time.Duration) error {
	return r.client.Set(ctx, keyPrefix+url, []byte(result), ttl).Err()
}

func (r *Redis) Ping(ctx context.Context) error { return r.client.Ping(ctx).Err() }

func (r *Redis) Close() error { return r.client.Close() }
