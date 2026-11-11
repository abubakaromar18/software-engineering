package dev.omar.supportdesk.config;

import dev.omar.supportdesk.chain.SupportHandler;

/** Builds one handler instance from its settings. Registered in a {@link HandlerRegistry} under a type name. */
@FunctionalInterface
public interface HandlerFactory {

    SupportHandler create(HandlerSettings settings);
}
