# Runtime Lifecycle and Graceful Shutdown

- NestJS đảm bảo thứ tự giữa các phase (`onModuleDestroy` → `beforeApplicationShutdown` → `onApplicationShutdown`), không đảm bảo thứ tự provider trong cùng phase. Consumer phải dừng ở phase trước provider đóng tài nguyên dùng chung.
- Mỗi shutdown path có một deadline tổng duy nhất. Các bước tuần tự dùng phần budget còn lại; cooperative cancellation ngăn bắt đầu work mới nhưng I/O đang chạy vẫn cần `Promise.race` với deadline.
- Theo dõi in-flight work và kiểm tra cancellation trước từng đơn vị công việc, không chỉ giữa các page. Timer phải được dừng và lượt đang chạy phải được chờ trong budget.
- Cleanup độc lập dùng `Promise.allSettled`, kiểm tra từng rejection, và vẫn chạy bước cleanup tiếp theo. Resource phải được đặt trong `try/finally` ngay sau khi acquisition thành công.
- `ioredis.quit()`, BullMQ `Queue.close()`/`Worker.close()` và Node `server.close()` có thể chờ vô hạn hoặc cache promise lần gọi đầu. Race graceful close với deadline rồi dùng primitive force-close phù hợp (`disconnect()`/`closeAllConnections()`); mọi fallback promise vẫn phải được await/catch.
- `Promise.race` phải phân biệt success, rejection và timeout; deadline chỉ giới hạn thời gian caller chờ, không thực sự hủy promise gốc.
