# LemonTea APK (Flet + GitHub Actions)

Mã nguồn ứng dụng Android **LemonTea** (Sol's RNG Biome Sniper) viết bằng **Python + Flet**, kèm sẵn **GitHub Actions** để tự động biên dịch ra file **`LemonTea.apk`** hoàn toàn miễn phí (không cần cài Android Studio).

## Cách tạo file `LemonTea.apk` trên GitHub (5 bước)
1. Đăng nhập **GitHub** (tạo tài khoản miễn phí nếu chưa có) → bấm **New repository** → đặt tên `LemonTea-APK` (để Public hoặc Private đều được) → bấm **Create repository**.
2. Giải nén file **`LemonTea-APK.zip`** trên máy tính hoặc điện thoại.
3. Tải toàn bộ các file và thư mục bên trong `LemonTea-APK/` lên repository vừa tạo (đảm bảo giữ nguyên thư mục `.github/workflows/build-apk.yml`, `pyproject.toml` và `src/`).
4. Chuyển sang tab **Actions** trên GitHub → chọn workflow **Build LemonTea APK** → nếu chưa tự chạy thì bấm **Run workflow**.
5. Chờ khoảng **5–10 phút** để build xong → bấm vào lượt chạy có dấu tích xanh → cuộn xuống mục **Artifacts** và tải **`LemonTea-APK`** về, giải nén lấy file **`LemonTea.apk`** cài vào điện thoại Android.

## Lưu ý khi cài trên điện thoại
- Bật **Cài đặt ứng dụng không rõ nguồn gốc** khi cài file `.apk`.
- Vào **Cài đặt → Ứng dụng → LemonTea → Pin** chọn **Không hạn chế** để app không bị tắt khi bạn chuyển sang Roblox.
