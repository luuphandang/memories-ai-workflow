# Example Feature — Data Flow

```text
User/System input
  → validation
  → application/service layer
  → persistence/integration
  → result/event
```

- Luồng nghiệp vụ chi tiết: `[BỔ SUNG THEO TÍNH NĂNG]`
- Module, database, queue hoặc service thực tế: `[BỔ SUNG THEO DỰ ÁN]`
- Transaction, idempotency và concurrency: `[BỔ SUNG THEO DỰ ÁN]`
