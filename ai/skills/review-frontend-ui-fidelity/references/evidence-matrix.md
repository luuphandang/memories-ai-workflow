# Evidence matrix

Represent every required comparison as one JSON entry:

```json
{
  "route": "/example",
  "viewport": "375x812",
  "state": "populated",
  "reference": "path/to/reference.png",
  "actual": "path/to/actual.png",
  "status": "passed"
}
```

Use at least one mobile, tablet and desktop viewport for each route unless the task defines different sizes. Add entries for empty, modal/open, validation and other risk states instead of hiding them in notes.
