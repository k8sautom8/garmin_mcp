docker build --platform linux/amd64 -t sybadm/gramin-mcp:V1.0 -f Dockerfile .
docker tag sybadm/gramin-mcp:V1.0 registry.ajlab.uk/sybadm/gramin-mcp:V1.0
docker push  registry.ajlab.uk/sybadm/gramin-mcp:V1.0

