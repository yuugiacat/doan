import os

from pydantic_settings import BaseSettings


def _parse_origins(raw: str) -> list[str]:
    return [o.strip() for o in raw.split(",") if o.strip()]


class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    # CORS_ORIGINS có thể set qua env var, comma-separated.
    # Mặc định gồm localhost (dev). Trên Render thêm domain Vercel.
    CORS_ORIGINS: list[str] = _parse_origins(
        os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:3000",
        )
    )

    # Persistent storage (optional) — set ở Render env vars
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    ADMIN_KEY: str = os.getenv("ADMIN_KEY", "")

    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Face detection
    FACE_DETECTION_CONFIDENCE: float = 0.7
    FACE_ABSENT_SHORT_THRESHOLD_MS: int = 10_000

    # Gaze / EAR
    EAR_BLINK_THRESHOLD: float = 0.22   # mắt "nhắm" — nâng nhẹ để bắt cả mắt lim dim/nhắm hờ
    EAR_DROWSY_THRESHOLD: float = 0.26  # mắt lim dim (chưa nhắm hẳn nhưng đã sụp mí)
    EAR_BLINK_MAX_MS: int = 400
    EAR_EYES_CLOSED_MIN_MS: int = 400

    # Head pose (degrees)
    HEAD_YAW_THRESHOLD: float = 20.0
    HEAD_PITCH_DOWN_THRESHOLD: float = -15.0
    HEAD_PITCH_UP_THRESHOLD: float = 15.0
    HEAD_FACING_YAW_MAX: float = 15.0
    HEAD_FACING_PITCH_MAX: float = 15.0

    # Body & hands
    HAND_NEAR_FACE_THRESHOLD_PX: float = 0.12  # normalized 0-1
    LEAN_THRESHOLD_RATIO: float = 0.15
    MOUTH_OPEN_THRESHOLD: float = 0.05          # lip distance normalized
    MOUTH_OPEN_MIN_MS: int = 1_000
    YAWN_MIN_MS: int = 2_000

    # Composite thresholds (ms)
    GAZE_OFF_LOOKING_AWAY_MS: int = 5_000   # nới: cho phép liếc nhìn ngắn không bị flag
    HEAD_TURNED_LOOKING_AWAY_MS: int = 5_000
    EYES_CLOSED_DROWSY_MS: int = 1_200      # nhắm mắt >1.2s → ngủ (trước 2s — bắt nhanh hơn)
    DROWSY_EYES_LOW_MS: int = 4_000          # mắt lim dim liên tục ≥4s → ngủ gật
    HEAD_DOWN_DOZY_MS: int = 6_000           # đầu cúi + mắt mỏi ≥6s (không viết) → ngủ gật
    YAWN_COUNT_WINDOW_S: int = 60
    YAWN_COUNT_DROWSY: int = 2
    PHONE_DISTRACTION_MIN_MS: int = 30_000  # 30s đầu cúi không viết → điện thoại
    PHONE_DETECTED_MIN_MS: int = 2_000     # điện thoại xuất hiện ≥2s → phone distraction
    PHONE_USE_DURATION_MS: int = 60_000    # sao nhãng liên tục ≥60s → phone distraction
    HEAD_TILT_THRESHOLD: float = 35.0     # nghiêng đầu ≥35° → có thể đọc phone ngang (cao để không nhầm với khi quay đầu)
    READING_MIN_MS: int = 1_000            # 1s nhìn thẳng màn hình = đang đọc
    ACTIVELY_ENGAGED_MIN_MS: int = 10_000
    THINKING_HAND_MIN_MS: int = 5_000
    PASSIVE_WATCHING_MIN_MS: int = 30_000

    # Attention scoring — mô hình chỉ trừ (điểm đi xuống là không hồi lại)
    SCORE_DISTRACTION_RATE_PER_S: float = 1.0   # điểm trừ/giây khi sao nhãng
    SCORE_SLEEPY_RATE_PER_S: float = 3.0         # điểm trừ/giây khi ngủ gật / nhắm mắt — trừ mạnh để data phản ánh rõ việc ngủ

    # Alert triggers (seconds)
    ALERT_PARTIALLY_FOCUSED_S: int = 60
    ALERT_DISTRACTED_S: int = 30
    ALERT_DROWSY_S: int = 8                  # cảnh báo sớm hơn khi có dấu hiệu ngủ

    # Privacy
    STORE_RAW_FRAMES: bool = False
    DATA_RETENTION_DAYS: int = 30

    CALIBRATION_DURATION_S: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
