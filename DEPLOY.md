# Deploy GenesisL1 Insights

The website overlay contains only these paths:

```text
insights/
evidence/stake-distribution/
```

Extract it into the existing `genesisl1.com` document root with overwrite enabled. Files elsewhere on the website are not included and are therefore left unchanged.

```bash
unzip -o GenesisL1_Insights_WEBROOT_OVERLAY_2026-09-21.zip \
  -d /path/to/genesisl1.com/document-root
```

