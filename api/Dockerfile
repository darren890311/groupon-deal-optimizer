# --- build stage ---
FROM golang:1.26-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /api .

# --- runtime stage (tiny, non-root, no shell) ---
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /api /api
EXPOSE 8080
USER nonroot:nonroot
ENTRYPOINT ["/api"]
