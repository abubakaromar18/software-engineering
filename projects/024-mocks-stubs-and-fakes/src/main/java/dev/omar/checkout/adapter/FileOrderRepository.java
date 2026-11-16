package dev.omar.checkout.adapter;

import dev.omar.checkout.domain.CustomerId;
import dev.omar.checkout.domain.Money;
import dev.omar.checkout.domain.Order;
import dev.omar.checkout.domain.OrderId;
import dev.omar.checkout.domain.OrderLine;
import dev.omar.checkout.domain.Sku;
import dev.omar.checkout.port.DuplicateOrderException;
import dev.omar.checkout.port.OrderRepository;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.net.URLDecoder;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

/**
 * A "real" adapter that persists orders as an append-only text file, one order per line:
 *
 * <pre>orderId|customer|placedAt|transactionId|SKU:qty:unitCents,SKU:qty:unitCents</pre>
 *
 * Free-text fields are URL-encoded so they cannot contain the separators. It stands in for a
 * database adapter here: slower, touches the file system, and is the thing the in-memory fake
 * imitates. Both run the same contract tests.
 */
public final class FileOrderRepository implements OrderRepository {

    private static final String FIELD = "|";
    private static final String LINE = ",";
    private static final String PART = ":";

    private final Path file;

    public FileOrderRepository(Path file) {
        this.file = Objects.requireNonNull(file, "file");
    }

    @Override
    public synchronized void save(Order order) {
        if (findById(order.id()).isPresent()) {
            throw new DuplicateOrderException(order.id());
        }
        try {
            Files.writeString(file, encode(order) + System.lineSeparator(), StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (IOException e) {
            throw new UncheckedIOException("could not write " + file, e);
        }
    }

    @Override
    public synchronized Optional<Order> findById(OrderId id) {
        return readAll().stream().filter(o -> o.id().equals(id)).findFirst();
    }

    @Override
    public synchronized List<Order> findByCustomer(CustomerId customer) {
        return readAll().stream().filter(o -> o.customer().equals(customer)).toList();
    }

    private List<Order> readAll() {
        if (!Files.exists(file)) {
            return List.of();
        }
        try {
            List<Order> result = new ArrayList<>();
            for (String row : Files.readAllLines(file, StandardCharsets.UTF_8)) {
                if (!row.isBlank()) {
                    result.add(decode(row));
                }
            }
            return result;
        } catch (IOException e) {
            throw new UncheckedIOException("could not read " + file, e);
        }
    }

    private static String encode(Order order) {
        List<String> lines = order.lines().stream()
                .map(l -> l.sku().code() + PART + l.quantity() + PART + l.unitPrice().cents())
                .toList();
        return String.join(FIELD,
                escape(order.id().value()),
                escape(order.customer().value()),
                order.placedAt().toString(),
                escape(order.paymentTransactionId()),
                String.join(LINE, lines));
    }

    private static Order decode(String row) {
        String[] fields = row.split("\\" + FIELD, -1);
        if (fields.length != 5) {
            throw new IllegalStateException("corrupt order row: " + row);
        }
        List<OrderLine> lines = new ArrayList<>();
        for (String encodedLine : fields[4].split(LINE)) {
            String[] parts = encodedLine.split(PART);
            lines.add(new OrderLine(new Sku(parts[0]), Integer.parseInt(parts[1]),
                    Money.ofCents(Long.parseLong(parts[2]))));
        }
        return new Order(new OrderId(unescape(fields[0])), new CustomerId(unescape(fields[1])),
                lines, Instant.parse(fields[2]), unescape(fields[3]));
    }

    private static String escape(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8);
    }

    private static String unescape(String value) {
        return URLDecoder.decode(value, StandardCharsets.UTF_8);
    }
}
