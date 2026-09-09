# Public hosting health gate

GRAIL production is healthy only when the deployed GitHub Pages URL serves both:

- HTML containing `GRAIL`
- `data/opportunities.json` containing a `candidates` payload

The Pages workflow retries public delivery after deployment and fails the run if the public site does not become reachable. This prevents a successful artifact deployment from being mistaken for a working user-facing site.
