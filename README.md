```bash
pip install -r requirements.txt
```
### set ssl shit:
```bach
unset SSL_CERT_FILE REQUESTS_CA_BUNDLE
python -c "import certifi,os; print(certifi.where())"
export REQUESTS_CA_BUNDLE="$(python -c 'import certifi; print(certifi.where())')"
export SSL_CERT_FILE="$REQUESTS_CA_BUNDLE"
```

## data presentation structure:
### Detail Levels from Top to bottom:

1. General summary:
   * Major Current trends of the industry and market (summary of each category summary)
   * Link to each category summary (next level down)
   
2. Summaries of a category (Competitive intel & new SKUs, Consumer signals & UGC, etc.):
    * Summary for a given category
    * Link to the detailed articles (next level down)

3. Article:
    * Summary for a given article
    * Link to the article source
