    @handle_exception("LoginError", "Login with retry")
    @RetryManager(max_attempts=Config.LOGIN_RETRY_ATTEMPTS, base_delay=Config.LOGIN_RETRY_DELAY)
    async def login_with_retry(self) -> tuple[bool, str]:
        """Login with retry logic."""
