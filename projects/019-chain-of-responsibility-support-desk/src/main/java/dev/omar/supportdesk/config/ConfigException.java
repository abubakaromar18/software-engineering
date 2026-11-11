package dev.omar.supportdesk.config;

import java.io.Serial;

/** The chain configuration is missing, malformed or inconsistent. Messages name the offending key. */
public final class ConfigException extends RuntimeException {

    @Serial
    private static final long serialVersionUID = 1L;

    public ConfigException(String message) {
        super(message);
    }

    public ConfigException(String message, Throwable cause) {
        super(message, cause);
    }
}
