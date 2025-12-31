"""Recipe Graph Engine 서버 실행"""

import uvicorn
from config.settings import get_settings


def main():
    settings = get_settings()
    uvicorn.run(
        "src.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
