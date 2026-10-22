"""HTTP layer: request parsing, validation and response shaping only.

No business logic belongs in this package — routers delegate to `app.services`
so that every algorithm stays unit-testable without an HTTP server.
"""
