package dev.omar.checkout.adapter;

import static dev.omar.checkout.Fixtures.BOOK;
import static dev.omar.checkout.Fixtures.MUG;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

class InMemoryInventoryTest {

    @Test
    void reserveIsAllOrNothing() {
        InMemoryInventory inventory = new InMemoryInventory(Map.of(BOOK, 3));

        assertFalse(inventory.reserve(BOOK, 4));
        assertEquals(3, inventory.available(BOOK));
        assertTrue(inventory.reserve(BOOK, 3));
        assertEquals(0, inventory.available(BOOK));
    }

    @Test
    void unknownSkuHasNoStockAndReleaseAddsIt() {
        InMemoryInventory inventory = new InMemoryInventory(Map.of());

        assertFalse(inventory.reserve(MUG, 1));
        inventory.release(MUG, 2);
        assertEquals(2, inventory.available(MUG));
    }

    @Test
    void rejectsNonPositiveQuantitiesAndNegativeStock() {
        InMemoryInventory inventory = new InMemoryInventory(Map.of(BOOK, 1));

        assertThrows(IllegalArgumentException.class, () -> inventory.reserve(BOOK, 0));
        assertThrows(IllegalArgumentException.class, () -> inventory.release(BOOK, -1));
        assertThrows(IllegalArgumentException.class, () -> new InMemoryInventory(Map.of(BOOK, -1)));
    }

    @Test
    void concurrentReservationsNeverOversell() throws InterruptedException {
        InMemoryInventory inventory = new InMemoryInventory(Map.of(BOOK, 100));
        AtomicInteger successes = new AtomicInteger();
        ExecutorService pool = Executors.newFixedThreadPool(8);
        for (int i = 0; i < 1_000; i++) {
            pool.execute(() -> {
                if (inventory.reserve(BOOK, 1)) {
                    successes.incrementAndGet();
                }
            });
        }
        pool.shutdown();
        assertTrue(pool.awaitTermination(10, TimeUnit.SECONDS));

        assertEquals(100, successes.get());
        assertEquals(0, inventory.available(BOOK));
    }
}
