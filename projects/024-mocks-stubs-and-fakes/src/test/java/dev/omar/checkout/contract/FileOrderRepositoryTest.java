package dev.omar.checkout.contract;

import static dev.omar.checkout.Fixtures.ADA;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import dev.omar.checkout.adapter.FileOrderRepository;
import dev.omar.checkout.domain.Order;
import dev.omar.checkout.domain.OrderId;
import dev.omar.checkout.port.OrderRepository;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Optional;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

@DisplayName("Contract: FileOrderRepository (real adapter)")
class FileOrderRepositoryTest extends OrderRepositoryContract {

    @TempDir
    Path dir;

    @Override
    protected OrderRepository newRepository() {
        return new FileOrderRepository(dir.resolve("orders.db"));
    }

    // Behaviour specific to this adapter lives beside the shared contract, not in it.

    @Test
    void ordersSurviveAReopen() {
        Path file = dir.resolve("persisted.db");
        Order order = order("ORD-1", ADA);
        new FileOrderRepository(file).save(order);

        assertEquals(Optional.of(order), new FileOrderRepository(file).findById(order.id()));
    }

    @Test
    void aCorruptFileIsReportedNotSilentlySkipped() throws IOException {
        Path file = dir.resolve("corrupt.db");
        Files.writeString(file, "not|an|order\n");

        assertThrows(IllegalStateException.class, () -> new FileOrderRepository(file).findById(new OrderId("x")));
    }
}
