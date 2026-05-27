from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Face detection
    FACE_DETECTION_CONFIDENCE: float = 0.7
    FACE_ABSENT_SHORT_THRESHOLD_MS: int = 10_000

    # Gaze / EAR
    EAR_BLINK_THRESHOLD: float = 0.2
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
    GAZE_OFF_LOOKING_AWAY_MS: int = 3_000
    HEAD_TURNED_LOOKING_AWAY_MS: int = 3_000
    EYES_CLOSED_DROWSY_MS: int = 2_000
    YAWN_COUNT_WINDOW_S: int = 60
    YAWN_COUNT_DROWSY: int = 2
    PHONE_DISTRACTION_MIN_MS: int = 30_000  # 30s đầu cúi không viết → điện thoại
    PHONE_DETECTED_MIN_MS: int = 2_000     # điện thoại xuất hiện ≥2s → phone distraction
    PHONE_USE_DURATION_MS: int = 60_000    # sao nhãng liên tục ≥60s → phone distraction
    HEAD_TILT_THRESHOLD: float = 20.0     # nghiêng đầu ≥20° → có thể đọc phone ngang
    READING_MIN_MS: int = 1_000            # 1s nhìn thẳng màn hình = đang đọc
    ACTIVELY_ENGAGED_MIN_MS: int = 10_000
    THINKING_HAND_MIN_MS: int = 5_000
    PASSIVE_WATCHING_MIN_MS: int = 30_000

    # Attention scoring — health-bar model (điểm bắt đầu 100, trừ khi sao nhãng, cộng khi không)
    SCORE_DISTRACTION_RATE_PER_S: float = 1.0   # điểm trừ/giây khi sao nhãng
    SCORE_SLEEPY_RATE_PER_S: float = 3.0         # điểm trừ/giây khi ngủ gật / nhắm mắt — trừ mạnh để data phản ánh rõ việc ngủ
    SCORE_ENGAGED_RATE_PER_S: float = 0.5        # điểm cộng/giây khi tập trung chủ động
    SCORE_NEUTRAL_RATE_PER_S: float = 0.2        # điểm cộng/giây khi ngồi yên (không sao nhãng)

    # Alert triggers (seconds)
    ALERT_PARTIALLY_FOCUSED_S: int = 60
    ALERT_DISTRACTED_S: int = 30
    ALERT_DROWSY_S: int = 15

    # Privacy
    STORE_RAW_FRAMES: bool = False
    DATA_RETENTION_DAYS: int = 30

    CALIBRATION_DURATION_S: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
