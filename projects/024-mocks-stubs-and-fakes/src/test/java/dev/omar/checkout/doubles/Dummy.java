package dev.omar.checkout.doubles;

import java.lang.reflect.Proxy;

/**
 * DUMMY — an object passed only to satisfy a parameter list. It is never meant to be used, so
 * this one fails the test loudly if it is. That turns "this collaborator is irrelevant to this
 * path" into an assertion instead of an assumption.
 */
public final class Dummy {

    private Dummy() {
    }

    public static <T> T of(Class<T> type) {
        Object proxy = Proxy.newProxyInstance(type.getClassLoader(), new Class<?>[] {type}, (self, method, args) ->
                switch (method.getName()) {
                    case "toString" -> "Dummy<" + type.getSimpleName() + ">";
                    case "hashCode" -> System.identityHashCode(self);
                    case "equals" -> self == args[0];
                    default -> throw new AssertionError(
                            "dummy " + type.getSimpleName() + "." + method.getName() + "() must not be called");
                });
        return type.cast(proxy);
    }
}
