# Learning Analytics AI

> Hệ thống phân tích hành vi học tập qua webcam, sử dụng Computer Vision và Learning Analytics để nhận diện trạng thái học/sao nhãng của người học và đưa ra phản hồi cải thiện.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Mục lục

- [Giới thiệu](#giới-thiệu)
- [Tính năng chính](#tính-năng-chính)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Behavior Vocabulary (CHI TIẾT)](#behavior-vocabulary-chi-tiết)
- [Phân tích trường hợp Học vs Sao nhãng](#phân-tích-trường-hợp-học-vs-sao-nhãng)
- [Thuật toán Attention Scoring](#thuật-toán-attention-scoring)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Database Schema](#database-schema)
- [Cài đặt](#cài-đặt)
- [Đạo đức và quyền riêng tư](#đạo-đức-và-quyền-riêng-tư)
- [Roadmap](#roadmap)
- [Tác giả](#tác-giả)

---

## Giới thiệu

**Learning Analytics AI** là đồ án nghiên cứu kết hợp **Computer Vision** và **Learning Analytics**, xây dựng hệ thống web có khả năng:

1. **Quan sát** người học qua webcam trong suốt phiên học
2. **Nhận diện** các hành vi cụ thể (atomic behaviors)
3. **Suy luận** trạng thái học tập (composite behaviors) — phân biệt rõ học vs sao nhãng
4. **Đánh giá** mức độ engagement và đưa ra phản hồi

### Vấn đề giải quyết

Trong môi trường học online, giáo viên khó nắm bắt engagement của học sinh, và bản thân học sinh cũng khó tự nhận thức lúc nào mình sao nhãng. Hệ thống cung cấp **phản hồi khách quan, định lượng** dựa trên hành vi quan sát được.

### Điểm đặc sắc

- **Behavior Vocabulary 2 lớp**: tách biệt rõ **atomic behaviors** (tín hiệu thô từ detector) và **composite behaviors** (trạng thái suy diễn) — đảm bảo mỗi event có ý nghĩa rõ ràng, không nhập nhằng
- **Phân biệt tinh tế**: cùng tư thế `head_down` có thể là *ghi chép* (tập trung) hoặc *ngủ gật* (sao nhãng) — hệ thống phân biệt được nhờ kết hợp đa tín hiệu
- **Privacy-first**: không lưu video/ảnh, chỉ lưu events đã trừu tượng hóa
- **Closed-loop feedback**: cảnh báo realtime + lời khuyên sau phiên

---

## Tính năng chính

### Quan sát realtime
- Kết nối webcam qua trình duyệt
- Trích xuất features bằng MediaPipe.js trên client (face landmarks, pose, iris)
- Nhận diện 7 biểu cảm cơ bản (FER2013)
- Truyền features qua WebSocket (không truyền frame)

### Nhận diện hành vi
- 5 nhóm atomic events: Presence, Gaze, Head Pose, Facial Expression, Body & Hands
- 9 composite events suy diễn (xem chi tiết bên dưới)
- Mỗi event có timestamp, duration, confidence

### Đánh giá engagement
- Điểm tập trung 0-100 mỗi 5 giây (rolling window)
- 4 trạng thái: `focused` / `partially_focused` / `distracted` / `drowsy_or_absent`
- Phát hiện sự kiện đặc biệt: ngủ gật, dùng điện thoại, rời chỗ

### Phân tích phiên học
- Timeline điểm tập trung
- Heatmap biểu cảm
- Thống kê: % tập trung, peak focus, số lần distraction, nguyên nhân chính
- So sánh giữa các phiên

### Phản hồi
- **Realtime alert** khi sao nhãng kéo dài ≥ 30s
- **Post-session advice** dựa trên pattern phát hiện được
- **Báo cáo định kỳ** theo tuần/tháng

---

## Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ Webcam +     │  │  Dashboard   │  │  Session Report      │   │
│  │ MediaPipe.js │  │  realtime    │  │  + Timeline          │   │
│  └──────┬───────┘  └──────────────┘  └──────────────────────┘   │
└─────────┼───────────────────────────────────────────────────────┘
          │ WebSocket: features only (KHÔNG gửi frame)
          │ REST API: auth, sessions, reports
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                       BACKEND (FastAPI)                         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  1. STREAMING LAYER                                     │    │
│  │  WebSocket Manager → Feature Receiver                   │    │
│  └─────────────────────┬───────────────────────────────────┘    │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  2. DETECTOR LAYER (server-side)                        │    │
│  │  Emotion Classifier (FER pretrained, optional on srv)   │    │
│  │  Features → Atomic Event Encoder                        │    │
│  └─────────────────────┬───────────────────────────────────┘    │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  3. ANALYTICS LAYER                                     │    │
│  │  Atomic → Composite Inference → Attention Scorer        │    │
│  │  Session Analyzer                                       │    │
│  └─────────────────────┬───────────────────────────────────┘    │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  4. RECOMMENDATION LAYER                                │    │
│  │  Alert Generator | Advice Generator                     │    │
│  └─────────────────────┬───────────────────────────────────┘    │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  STORAGE LAYER                                          │    │
│  │  Event Buffer → Batch Writer → PostgreSQL               │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Luồng dữ liệu

```
Webcam (480p, 10 FPS)
   ↓
Frontend: MediaPipe.js extract features
  • Face landmarks (468 points)
  • Pose landmarks (33 points)
  • Hand landmarks (21 points × 2)
  • Iris position
   ↓ WebSocket (JSON, ~5 KB/s)
Backend Feature Receiver
   ↓
Atomic Event Encoder (rule-based)
  • Tính góc đầu, vector ánh mắt, tỷ lệ EAR
  • So với ngưỡng → atomic event
   ↓
Composite Inference (rule-based)
  • Kết hợp đa atomic event → composite event
   ↓
Attention Scorer
  • Window 5s → score 0-100
   ↓
   ├──→ Frontend (hiển thị realtime)
   ├──→ Alert Generator
   └──→ Event Buffer → PostgreSQL (batch insert 10s)

Khi session kết thúc:
   ↓
Session Analyzer → Advice Generator → Report
```

---

## Công nghệ sử dụng

### Backend
- **Python 3.10+**
- **FastAPI** — Web framework + WebSocket
- **SQLAlchemy + Alembic** — ORM + migrations
- **PostgreSQL** — Database chính
- **Pydantic** — Validation
- **NumPy, Pandas** — Xử lý dữ liệu
- **ONNX Runtime** — Inference emotion model (pretrained FER+ hoặc HSEmotion)

### Frontend
- **React 18 + TypeScript**
- **Vite** — Build tool
- **TailwindCSS** — Styling
- **Recharts** — Biểu đồ
- **Zustand** — State management
- **MediaPipe Tasks Vision (Web)** — CV trên client

### DevOps
- **Docker + Docker Compose**
- **Pytest** — Testing

---

## Behavior Vocabulary (CHI TIẾT)

> **Đây là phần trung tâm của hệ thống.** Vocabulary chia làm 2 lớp: **Atomic** (đo trực tiếp từ detector) và **Composite** (suy diễn từ tổ hợp atomic). Sự tách biệt này đảm bảo mỗi event có một nghĩa, không nhập nhằng.

### Nguyên tắc thiết kế

1. **Mỗi atomic event là một sự kiện đo được trực tiếp** từ output của một detector, không kèm diễn giải nghĩa.
2. **Composite event là kết quả suy diễn** bằng rule từ tổ hợp atomic event, là cái có ý nghĩa giáo dục (học/sao nhãng).
3. **Mỗi event đều có `duration` và `timestamp`** — phân biệt liếc nhìn 0.5s với quay đầu thực sự 30s.
4. **Mỗi event có `confidence`** từ detector — loại bỏ event độ tin cậy thấp trước khi vào DB.

---

### A. ATOMIC EVENTS (tín hiệu thô)

#### A1. Presence — sự hiện diện
*Nguồn: Face Detector (MediaPipe Face Detection)*

| Event | Điều kiện kích hoạt | Attributes |
|---|---|---|
| `face_present` | Phát hiện 1 khuôn mặt với confidence ≥ 0.7 | `confidence` |
| `face_absent_short` | Không phát hiện mặt liên tục < 10s | `duration_ms` |
| `face_absent_long` | Không phát hiện mặt liên tục ≥ 10s | `duration_ms` |
| `multiple_faces` | Phát hiện > 1 khuôn mặt | `face_count` |

**Lý do tách short/long**: Cúi nhặt đồ, uống nước, lấy giấy bút (~5s) là hành vi học bình thường, không phải "rời chỗ".

---

#### A2. Gaze — ánh mắt
*Nguồn: MediaPipe Iris + Face Landmarks*

| Event | Điều kiện kích hoạt | Attributes |
|---|---|---|
| `gaze_on_screen` | Vector ánh mắt nằm trong vùng màn hình ước tính | `confidence` |
| `gaze_off_screen` | Vector ánh mắt lệch khỏi vùng màn hình | `direction` ∈ {left, right, up, down}, `duration_ms` |
| `blink` | Eye Aspect Ratio (EAR) < 0.2 trong 100-400ms | `duration_ms` |
| `eyes_closed` | EAR < 0.2 ≥ 400ms | `duration_ms` |

**Lý do gộp `eyes_closed_short/long`**: Một event duy nhất với `duration_ms`, để composite layer phân loại (drowsy nếu ≥ 2s, suy nghĩ nếu 400ms-1s).

**Lưu ý**: Vùng màn hình ước tính sẽ được calibrate ở 30s đầu phiên (xem [Calibration](#calibration)).

---

#### A3. Head Pose — tư thế đầu
*Nguồn: MediaPipe Face Mesh → tính 3 góc Euler (yaw, pitch, roll)*

| Event | Điều kiện kích hoạt | Attributes |
|---|---|---|
| `head_facing_screen` | \|yaw\| ≤ 15°, \|pitch\| ≤ 15° | `yaw`, `pitch` |
| `head_turned` | \|yaw\| > 20° | `direction` ∈ {left, right}, `angle_deg`, `duration_ms` |
| `head_down` | pitch < -15° | `angle_deg`, `duration_ms` |
| `head_up` | pitch > 15° | `angle_deg`, `duration_ms` |

**RẤT QUAN TRỌNG — sửa so với phiên bản trước**: 
- `head_down` **KHÔNG diễn giải là "ghi chép hoặc ngủ gật"** ở atomic layer. Nó chỉ là tín hiệu vật lý "đầu cúi xuống".
- Việc phân biệt ghi chép vs ngủ gật được xử lý ở **composite layer** bằng cách kết hợp với gaze, eyes_closed, hand events.

---

#### A4. Facial Expression — biểu cảm khuôn mặt
*Nguồn: Emotion classifier (pretrained FER+, output 7 lớp)*

| Event | Output gốc của model | Attributes |
|---|---|---|
| `expr_neutral` | neutral | `confidence` |
| `expr_happy` | happy | `confidence` |
| `expr_surprise` | surprise | `confidence` |
| `expr_sad` | sad | `confidence` |
| `expr_angry` | angry | `confidence` |
| `expr_fear` | fear | `confidence` |
| `expr_disgust` | disgust | `confidence` |

**Lưu ý đặt tên**: Dùng `expr_*` (biểu cảm) thay vì `emotion_*` (cảm xúc) vì:
- Đo được: chỉ là biểu hiện cơ mặt
- Không phải cảm xúc thực sự bên trong người học
- Trung thực về giới hạn của model

**KHÔNG có `expr_engaged`, `expr_confused`, `expr_bored` ở atomic layer** vì model FER không output các nhãn này. Chúng sẽ được suy diễn ở composite layer.

---

#### A5. Body & Hands — cơ thể, tay (THÊM MỚI, RẤT QUAN TRỌNG)
*Nguồn: MediaPipe Pose + Hands*

| Event | Điều kiện kích hoạt | Attributes |
|---|---|---|
| `hand_near_face` | Khoảng cách bất kỳ landmark tay → bbox mặt < ngưỡng | `which_hand` ∈ {left, right}, `duration_ms` |
| `hand_writing` | Tay ở vùng dưới khung hình, có cử động đều đặn, gaze hướng xuống | `duration_ms` |
| `hand_holding_phone_likely` | Tay cầm vật ngang ngực/bụng, gaze hướng xuống tay ≥ 3s | `confidence` (heuristic) |
| `mouth_open_wide` | Khoảng cách môi trên-dưới > ngưỡng, kéo dài 1-3s | `duration_ms` |
| `yawn` | `mouth_open_wide` + `eyes_closed` đồng thời, 2-5s | `duration_ms` |
| `stretch` | Cánh tay giơ cao đột ngột (cổ tay vượt trên vai) | `duration_ms` |
| `lean_forward` | Vai gần camera hơn baseline ≥ 15% | `duration_ms` |
| `lean_back` | Vai xa camera hơn baseline ≥ 15% | `duration_ms` |
| `talking_likely` | Môi cử động đều đặn ≥ 2s mà không phải ngáp | `duration_ms` |

**Tại sao thêm nhóm này quan trọng?**
- Giải quyết vấn đề `head_down` nhập nhằng (ghi chép vs ngủ gật)
- Bắt được hành vi sao nhãng phổ biến nhất: **dùng điện thoại**
- Phát hiện mệt mỏi sớm qua `yawn`, `stretch`
- Phân biệt engagement chủ động (`lean_forward`) vs thụ động (`lean_back`)

**Nếu MVP không kịp triển khai cả nhóm**: ưu tiên giữ `hand_near_face`, `hand_writing`, `mouth_open_wide`, `yawn`.

---

### B. COMPOSITE EVENTS (suy diễn từ atomic)

Composite events là **kết quả của rules** kết hợp nhiều atomic events trong cửa sổ thời gian. Đây là cái có ý nghĩa giáo dục thực sự.

| Composite Event | Rule | Diễn giải |
|---|---|---|
| `taking_notes` | `head_down` ∧ `hand_writing` ∧ ¬`eyes_closed` | **Học**: Đang ghi chép |
| `reading_screen` | `gaze_on_screen` ∧ `head_facing_screen` ∧ duration ≥ 5s | **Học**: Đang đọc |
| `thinking_pose` | `hand_near_face` ∧ (`gaze_on_screen` ∨ `gaze_off_screen.up`) ∧ `expr_neutral` ∧ ¬`eyes_closed` | **Học**: Đang suy nghĩ |
| `actively_engaged` | `lean_forward` ∧ `gaze_on_screen` ∧ duration ≥ 10s | **Học**: Tập trung chủ động |
| `passive_watching` | `gaze_on_screen` ∧ `head_facing_screen` ∧ `expr_neutral` ∧ `lean_back` ≥ 30s | **Trung tính**: Xem thụ động (có thể đang lười) |
| `drowsy` | `eyes_closed` ≥ 2s ∨ (`yawn` ≥ 2 lần trong 60s) ∨ (`head_down` ∧ `eyes_closed`) | **Sao nhãng**: Buồn ngủ |
| `looking_away` | `gaze_off_screen` ≥ 3s ∨ `head_turned` ≥ 3s | **Sao nhãng**: Nhìn ra ngoài |
| `phone_distraction` | `hand_holding_phone_likely` ∨ (`head_down` ∧ `gaze_off_screen.down` ∧ ¬`hand_writing`) ≥ 3s | **Sao nhãng**: Dùng điện thoại |
| `talking_to_someone` | `multiple_faces` ∨ (`talking_likely` ∧ `head_turned`) | **Sao nhãng**: Nói chuyện với người khác |
| `away_from_desk` | `face_absent_long` | **Sao nhãng**: Rời chỗ |
| `confused_likely` | `expr_surprise` ∨ `expr_fear` ∨ (lông mày nhíu lại với `gaze_on_screen` ≥ 3s) | **Cần hỗ trợ**: Có thể đang bối rối |
| `frustrated_likely` | `expr_angry` ∨ `expr_disgust` ≥ 5s với `gaze_on_screen` | **Cần hỗ trợ**: Có thể đang bực |

---

### C. Schema cho mỗi event (chuẩn lưu DB)

```python
{
  "event_id": "uuid",
  "session_id": "uuid",
  "event_type": "head_turned",           # tên event
  "category": "atomic" | "composite",
  "event_group": "head_pose",            # nhóm A1-A5 hoặc "composite"
  "timestamp_start": 1715500000.0,       # epoch seconds
  "timestamp_end": 1715500001.5,
  "duration_ms": 1500,
  "confidence": 0.87,
  "attributes": {                        # tùy event, JSON
    "direction": "left",
    "angle_deg": 35
  }
}
```

**Quy tắc lưu**:
- Atomic event chỉ lưu khi state thay đổi (state-change detection), không lưu mỗi frame
- Composite event lưu khi rule kích hoạt
- Confidence < 0.5 → loại bỏ, không lưu

---

## Phân tích trường hợp Học vs Sao nhãng

Phần này **liệt kê đầy đủ các tình huống thực tế** và cách hệ thống nhận diện. Đây là phần để check vocabulary có đủ không.

### Nhóm 1: HÀNH VI HỌC TẬP (tích cực)

| Tình huống thực tế | Atomic events kích hoạt | Composite event | Score impact |
|---|---|---|---|
| **Đang đọc tài liệu trên màn hình** | `face_present` + `gaze_on_screen` + `head_facing_screen` | `reading_screen` | +cao |
| **Đang ghi chép vào vở** | `face_present` + `head_down` + `hand_writing` | `taking_notes` | +cao |
| **Đang suy nghĩ, chống cằm** | `face_present` + `hand_near_face` + `gaze_on_screen` + `expr_neutral` | `thinking_pose` | +trung bình |
| **Đang suy nghĩ, ngước lên trần** | `face_present` + `gaze_off_screen.up` ngắn + `hand_near_face` | `thinking_pose` | +trung bình |
| **Cúi sát vào màn hình (tập trung cao)** | `lean_forward` + `gaze_on_screen` | `actively_engaged` | +cao |
| **Mỉm cười khi hiểu bài** | `expr_happy` + `gaze_on_screen` | (positive emotion) | +nhẹ |
| **Cúi xuống lấy giấy/bút (<5s)** | `face_absent_short` | (không alarm) | trung tính |
| **Uống nước nhanh** | `face_absent_short` hoặc `head_up` ngắn | (không alarm) | trung tính |

### Nhóm 2: HÀNH VI SAO NHÃNG (tiêu cực)

| Tình huống thực tế | Atomic events kích hoạt | Composite event | Score impact |
|---|---|---|---|
| **Nhìn ra cửa sổ kéo dài** | `gaze_off_screen.left/right` ≥ 3s | `looking_away` | -cao |
| **Quay sang nói chuyện với người khác** | `head_turned` + `multiple_faces` (nếu thấy) + `talking_likely` | `talking_to_someone` | -rất cao |
| **Cầm điện thoại, lướt mạng** | `head_down` + `gaze_off_screen.down` + `hand_holding_phone_likely` | `phone_distraction` | -rất cao |
| **Ngủ gật, gục đầu** | `head_down` + `eyes_closed` ≥ 2s | `drowsy` | -rất cao |
| **Mệt, ngáp nhiều lần** | `yawn` ≥ 2 lần/phút | `drowsy` | -cao |
| **Ngả ra ghế, nhìn vu vơ** | `lean_back` + `gaze_off_screen` + `expr_neutral` ≥ 30s | `passive_watching` (xu hướng disengaged) | -trung bình |
| **Rời chỗ đi đâu đó** | `face_absent_long` ≥ 10s | `away_from_desk` | -rất cao |
| **Vươn vai, duỗi người** | `stretch` + `head_up` | (không alarm — coi là nghỉ ngắn lành mạnh) | trung tính |

### Nhóm 3: HÀNH VI MƠ HỒ (cần phân biệt cẩn thận)

Đây là các trường hợp dễ bị nhầm. Vocabulary phải xử lý được:

| Tình huống | Có thể bị nhầm | Cách phân biệt đúng |
|---|---|---|
| **Đầu cúi xuống (head_down)** | Ghi chép hay ngủ gật? | Có `hand_writing` → `taking_notes`. Có `eyes_closed` → `drowsy`. Không có cả 2 → cần thêm tín hiệu (kiểm tra gaze direction) |
| **Mắt nhắm** | Đang nháy mắt, đang suy nghĩ, hay đang ngủ? | < 400ms → `blink`. 400ms-2s → có thể đang suy nghĩ (kèm `hand_near_face`?). ≥ 2s → `drowsy` |
| **Nhìn xuống** | Đang đọc trên bàn, hay đang xem điện thoại? | Có `hand_writing` → đang đọc/ghi trên bàn. Có `hand_holding_phone_likely` → `phone_distraction` |
| **Không thấy mặt** | Cúi nhặt đồ, hay đã rời đi? | < 10s → `face_absent_short` (không alarm). ≥ 10s → `face_absent_long` → `away_from_desk` |
| **Đầu quay sang** | Liếc nhìn nhanh, hay quay hẳn đi? | < 3s → liếc, không alarm. ≥ 3s → `looking_away` |
| **Biểu cảm `expr_surprise`** | Bối rối với bài, hay bị giật mình vì cái gì đó? | Có `gaze_on_screen` đồng thời → `confused_likely`. Có `gaze_off_screen` → ngoại cảnh, không alarm |
| **Miệng mở** | Đang ngáp hay đang nói? | Kèm `eyes_closed` → `yawn`. Không kèm, cử động đều → `talking_likely` |
| **Tay gần mặt** | Suy nghĩ hay ngứa/gãi? | Kèm `gaze_on_screen` + `expr_neutral` ≥ 5s → `thinking_pose`. Ngắn (<2s) → bỏ qua |

### Nhóm 4: HÀNH VI ĐẶC BIỆT (cần xử lý riêng)

| Tình huống | Xử lý |
|---|---|
| **Có người khác bước vào sau lưng** | `multiple_faces` — alert nhẹ, có thể là môi trường ồn |
| **Đeo kính phản chiếu màn hình** | Iris detector có thể nhiễu — giảm trọng số gaze, tăng trọng số head pose |
| **Ánh sáng yếu/ngược sáng** | Confidence của detector thấp → bỏ event, log warning UI gợi ý bật đèn |
| **Đeo khẩu trang** | Emotion detector fail → bỏ trọng số expression, chỉ dùng gaze + pose |
| **Webcam góc lệch** | Calibration phát hiện và yêu cầu chỉnh lại |
| **Nhiều màn hình** | Cần đánh dấu vùng màn hình chính khi calibrate |

---

## Thuật toán Attention Scoring

Điểm tập trung được tính trong cửa sổ trượt **5 giây**, cập nhật mỗi giây.

### Bước 1: Tính tỷ lệ thời gian từng nhóm composite trong window

```
focus_time   = thời gian {reading_screen, taking_notes, thinking_pose, actively_engaged}
neutral_time = thời gian {passive_watching, không có composite nào}
distract_time = thời gian {looking_away, phone_distraction, talking_to_someone, drowsy, away_from_desk}
```

### Bước 2: Weighted score

```python
attention_score = (
    1.00 * focus_time_ratio +
    0.50 * neutral_time_ratio +
    0.00 * distract_time_ratio
) * 100

# Trừ thêm penalty cho sự kiện nặng
if drowsy_in_window: attention_score -= 20
if phone_distraction_in_window: attention_score -= 30
if away_from_desk_in_window: attention_score -= 40

attention_score = max(0, min(100, attention_score))
```

### Bước 3: Smooth bằng EMA (Exponential Moving Average)

```python
score_smoothed = 0.7 * score_smoothed_prev + 0.3 * score_current
```

Tránh nhảy điểm đột ngột.

### Phân loại trạng thái

| Score | Trạng thái | Ý nghĩa |
|---|---|---|
| 80-100 | `focused` | Tập trung tốt |
| 50-79 | `partially_focused` | Tập trung vừa |
| 20-49 | `distracted` | Sao nhãng |
| 0-19 | `drowsy_or_absent` | Buồn ngủ hoặc rời khỏi |

### Trigger alert

- `partially_focused` kéo dài ≥ 60s → nudge nhẹ
- `distracted` kéo dài ≥ 30s → alert
- `drowsy_or_absent` ≥ 15s → alert mạnh (có thể kèm âm thanh)

---

## Cấu trúc thư mục

```
learning-analytics-ai/
│
├── backend/                              # FastAPI backend
│   ├── app/
│   │   ├── main.py                       # Entry point
│   │   ├── config.py                     # Settings
│   │   │
│   │   ├── api/v1/                       # REST API endpoints
│   │   │   ├── auth.py                   # Đăng ký, đăng nhập
│   │   │   ├── sessions.py               # CRUD phiên học
│   │   │   ├── analytics.py              # Truy vấn analytics
│   │   │   ├── reports.py                # Báo cáo phiên/tuần/tháng
│   │   │   └── recommendations.py        # Lời khuyên
│   │   │
│   │   ├── streaming/                    # WebSocket
│   │   │   ├── ws_manager.py             # Quản lý connections
│   │   │   ├── ws_handlers.py            # Xử lý message
│   │   │   └── feature_receiver.py       # Nhận features từ client
│   │   │
│   │   ├── services/
│   │   │   ├── detectors/
│   │   │   │   └── emotion_classifier.py # ONNX inference FER
│   │   │   │
│   │   │   ├── analytics/                # CORE — code chính ở đây
│   │   │   │   ├── vocabulary.py         # Định nghĩa tất cả event types
│   │   │   │   ├── atomic_encoder.py     # Features → atomic events
│   │   │   │   ├── composite_inferrer.py # Atomic → composite events
│   │   │   │   ├── attention_scorer.py   # Composite → score
│   │   │   │   └── session_analyzer.py   # Phân tích sau session
│   │   │   │
│   │   │   ├── recommendation/
│   │   │   │   ├── rules.py              # Rules cho alert/advice
│   │   │   │   ├── alert_generator.py    # Realtime alerts
│   │   │   │   └── advice_generator.py   # Post-session advice
│   │   │   │
│   │   │   └── calibration/
│   │   │       └── baseline.py           # 30s đầu phiên để baseline
│   │   │
│   │   ├── core/
│   │   │   ├── security.py               # JWT, hashing
│   │   │   ├── logging.py
│   │   │   └── privacy.py                # Anonymization, retention
│   │   │
│   │   ├── database/
│   │   │   ├── connection.py
│   │   │   ├── models/                   # SQLAlchemy ORM
│   │   │   │   ├── user.py
│   │   │   │   ├── session.py
│   │   │   │   ├── event.py              # Bảng events theo schema ở trên
│   │   │   │   └── report.py
│   │   │   ├── schemas/                  # Pydantic schemas
│   │   │   └── repositories/
│   │   │
│   │   ├── storage/
│   │   │   ├── event_buffer.py           # In-memory buffer
│   │   │   └── batch_writer.py           # Batch insert mỗi 10s
│   │   │
│   │   └── utils/
│   │
│   ├── tests/
│   │   ├── test_atomic_encoder.py        # Test mỗi atomic event
│   │   ├── test_composite_inferrer.py    # Test các trường hợp mơ hồ
│   │   └── test_attention_scorer.py
│   │
│   ├── migrations/                       # Alembic
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                             # React frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── LearningSession.tsx       # Trang học chính (webcam + score)
│   │   │   ├── Dashboard.tsx             # Tổng quan
│   │   │   ├── SessionReport.tsx         # Báo cáo phiên
│   │   │   └── History.tsx               # Lịch sử
│   │   ├── components/
│   │   │   ├── webcam/
│   │   │   │   ├── WebcamView.tsx
│   │   │   │   └── MediaPipeProcessor.tsx # Trích xuất features
│   │   │   ├── analytics/
│   │   │   │   ├── AttentionMeter.tsx    # Đồng hồ điểm realtime
│   │   │   │   ├── FocusTimeline.tsx
│   │   │   │   └── EmotionHeatmap.tsx
│   │   │   └── recommendation/
│   │   │       ├── AlertBanner.tsx
│   │   │       └── AdviceCard.tsx
│   │   ├── hooks/
│   │   │   ├── useWebcam.ts
│   │   │   ├── useMediaPipe.ts
│   │   │   └── useWebSocket.ts
│   │   ├── services/                     # API clients
│   │   ├── store/                        # Zustand
│   │   ├── websocket/
│   │   └── types/
│   ├── package.json
│   └── Dockerfile
│
├── ml/                                   # Research (không bắt buộc cho MVP)
│   ├── notebooks/
│   └── evaluation/
│
├── ml_models/                            # Pretrained models (gitignore)
│
├── docs/
│   ├── architecture.md
│   ├── api_spec.md
│   ├── database_schema.md
│   ├── behavior_vocabulary.md            # Bản chi tiết hơn của section trên
│   ├── attention_algorithm.md
│   └── ethics_and_privacy.md
│
├── scripts/
│   ├── setup.sh
│   ├── seed_db.py
│   └── download_models.py
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## Database Schema

### Bảng `users`
```sql
id UUID PK
email VARCHAR UNIQUE
hashed_password VARCHAR
created_at TIMESTAMP
```

### Bảng `sessions`
```sql
id UUID PK
user_id UUID FK -> users
started_at TIMESTAMP
ended_at TIMESTAMP NULL
calibration_baseline JSONB    -- Lưu baseline (góc đầu trung tính, vị trí mắt...)
overall_score FLOAT NULL      -- Tính khi session kết thúc
```

### Bảng `events`
```sql
id UUID PK
session_id UUID FK -> sessions
event_type VARCHAR            -- 'head_turned', 'taking_notes', ...
category VARCHAR              -- 'atomic' | 'composite'
event_group VARCHAR           -- 'gaze', 'head_pose', 'composite', ...
timestamp_start TIMESTAMP
timestamp_end TIMESTAMP
duration_ms INTEGER
confidence FLOAT
attributes JSONB              -- {direction, angle, ...}

INDEX (session_id, timestamp_start)
INDEX (event_type)
```

### Bảng `attention_scores`
```sql
id UUID PK
session_id UUID FK -> sessions
timestamp TIMESTAMP
score FLOAT                   -- 0-100
state VARCHAR                 -- focused/partially_focused/distracted/drowsy_or_absent

INDEX (session_id, timestamp)
```

### Bảng `alerts`
```sql
id UUID PK
session_id UUID FK -> sessions
timestamp TIMESTAMP
alert_type VARCHAR            -- nudge, alert, strong_alert
reason VARCHAR                -- composite event name
message TEXT
```

---

## Cài đặt

### Yêu cầu

- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL 15+** (hoặc Docker)
- **Webcam**

### Cài đặt nhanh với Docker

```bash
git clone https://github.com/yourusername/learning-analytics-ai.git
cd learning-analytics-ai
cp .env.example .env
docker-compose up -d

# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# API docs: http://localhost:8000/docs
```

### Cài đặt thủ công

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
createdb learning_analytics
alembic upgrade head
python ../scripts/download_models.py
uvicorn app.main:app --reload --port 8000

# Frontend
cd ../frontend
npm install
npm run dev
```

### Biến môi trường

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/learning_analytics
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=http://localhost:3000
MODEL_DIR=./ml_models
LOG_LEVEL=INFO
DATA_RETENTION_DAYS=30
STORE_RAW_FRAMES=false           # ALWAYS FALSE — không lưu ảnh
```

---

## Calibration

Mỗi phiên học bắt đầu với **30 giây calibration**:

1. Yêu cầu người học ngồi ở tư thế bình thường, nhìn vào màn hình
2. Ghi nhận giá trị baseline:
   - Góc yaw/pitch trung tính
   - Vị trí mắt khi nhìn 4 góc màn hình (yêu cầu nhìn 4 chấm)
   - EAR trung bình khi mắt mở
   - Vị trí vai (cho lean_forward/back)
3. Lưu vào `sessions.calibration_baseline`
4. Tất cả ngưỡng của atomic event sẽ tính tương đối với baseline này

Lý do: Mỗi người có hình thái khác nhau, ngưỡng cứng (như `pitch < -15°`) không đúng cho mọi người.

---

## Đạo đức và quyền riêng tư

- **Consent rõ ràng**: yêu cầu đồng ý trước khi bật webcam, hiển thị rõ thu thập gì
- **Không lưu hình ảnh hay video**: chỉ lưu events (số), `STORE_RAW_FRAMES=false` mặc định
- **Xử lý trên client tối đa**: MediaPipe.js chạy trên browser, chỉ features (~5KB/s) được gửi đi
- **Anonymization**: dữ liệu có thể được ẩn danh hóa
- **Data retention**: tự động xóa sau 30 ngày
- **Right to delete**: người dùng có quyền xóa toàn bộ dữ liệu của mình
- **Right to pause**: nút tạm dừng quan sát bất kỳ lúc nào

⚠️ Đây là đồ án nghiên cứu, không phải sản phẩm thương mại. Triển khai thực tế cần tuân thủ GDPR và quy định địa phương.

---

## Roadmap

### Giai đoạn 1 — Setup & Infrastructure (Tuần 1-2)
- [x] Setup cấu trúc thư mục, Git
- [ ] Database schema + ORM models (users, sessions, events, attention_scores)
- [ ] WebSocket pipeline FE-BE
- [ ] Frontend: webcam + MediaPipe.js trích xuất features
- [ ] Backend nhận features, log ra console

### Giai đoạn 2 — Behavior Vocabulary (Tuần 3-4)
- [ ] **`vocabulary.py`**: định nghĩa tất cả atomic + composite events (enum, schema)
- [ ] **`atomic_encoder.py`**: features → atomic events (rule + threshold)
- [ ] **`composite_inferrer.py`**: atomic → composite (rules ở Section B vocabulary)
- [ ] Unit test cho tất cả trường hợp ở section "Phân tích trường hợp" (đặc biệt nhóm 3 mơ hồ)
- [ ] Event buffer + batch write PostgreSQL

### Giai đoạn 3 — Scoring & UI (Tuần 5-6)
- [ ] **`attention_scorer.py`**: weighted score + EMA smoothing
- [ ] Dashboard: AttentionMeter realtime + FocusTimeline
- [ ] Calibration flow (30s đầu phiên)
- [ ] Consent flow + privacy controls

### Giai đoạn 4 — Recommendation & Polish (Tuần 7-8)
- [ ] Alert generator (rules theo composite event)
- [ ] Post-session advice generator
- [ ] Session report đầy đủ (timeline, heatmap, thống kê)
- [ ] Báo cáo đồ án + demo video

### Tương lai (sau đồ án)
- [ ] Multi-user classroom mode
- [ ] Mobile app
- [ ] Tích hợp LMS (Moodle, Canvas)
- [ ] ML model thay rule-based scoring
- [ ] So sánh nhóm học sinh
- [ ] A/B test các loại nudge/alert

---

## Hướng dẫn cho AI code agent

> Phần này dành riêng cho AI code agent (Claude Code, Cursor, etc.) khi implement đồ án này.

### Quy tắc khi code

1. **Mọi event mới phải khai báo trong `vocabulary.py` trước**, không hardcode tên event ở chỗ khác.
2. **Atomic encoder KHÔNG được output composite event** và ngược lại — đảm bảo tách lớp.
3. **Mọi rule trong `composite_inferrer.py` phải có unit test** với ít nhất 2 case: tích cực và tiêu cực.
4. **Confidence của event phải được propagate** từ detector tới DB, không discard.
5. **State-change detection**: atomic event chỉ emit khi state đổi, không emit mỗi frame.
6. **Tất cả ngưỡng (threshold)** phải đặt trong `config.py` hoặc tính tương đối từ calibration baseline, không hardcode magic number.
7. **WebSocket message** dùng JSON schema rõ ràng (xem `docs/api_spec.md`), không truyền bytes.
8. **Privacy**: không log frame, không log features ra console ở môi trường production.

### Thứ tự implement đề xuất

1. `vocabulary.py` — định nghĩa events trước
2. Schema DB + migrations
3. Mock data: tạo file JSON giả lập features để test pipeline không cần webcam
4. `atomic_encoder.py` + tests dùng mock data
5. `composite_inferrer.py` + tests (đặc biệt nhóm 3 mơ hồ)
6. WebSocket pipeline đầu cuối
7. `attention_scorer.py`
8. Frontend integration
9. Alert + Advice
10. Calibration

### Tài liệu nội bộ cần đọc

- `docs/behavior_vocabulary.md` — chi tiết hơn README
- `docs/attention_algorithm.md` — thuật toán scoring
- `docs/api_spec.md` — REST + WebSocket spec
- `docs/database_schema.md` — ERD

---

## Tác giả

**[Tên của bạn]**
- Trường: [Tên trường]
- Khoa: [Tên khoa]
- Email: [your.email@example.com]
- GitHub: [@yourusername](https://github.com/yourusername)

**Giảng viên hướng dẫn**: [Tên giảng viên]

---

## Tài liệu tham khảo

### Học thuật
- D'Mello, S., & Graesser, A. (2012). *Dynamics of affective states during complex learning*
- Whitehill, J. et al. (2014). *The Faces of Engagement: Automatic Recognition of Student Engagement*
- Kamath, A. et al. (2016). *DAiSEE: Dataset for Affective States in E-Environments*
- Dewan, M. A. A., et al. (2019). *Engagement detection in online learning: A review*

### Kỹ thuật
- [MediaPipe Documentation](https://developers.google.com/mediapipe)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)

---

## License

MIT License. Xem [`LICENSE`](LICENSE) để biết chi tiết.

---

<div align="center">

**Nếu đồ án này hữu ích, hãy cho một ⭐ trên GitHub!**

[⬆ Quay lại đầu trang](#learning-analytics-ai)

</div>
