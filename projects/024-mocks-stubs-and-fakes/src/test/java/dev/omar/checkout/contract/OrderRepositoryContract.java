package dev.omar.checkout.contract;

import static dev.omar.checkout.Fixtures.ADA;
import static dev.omar.checkout.Fixtures.BOOK;
import static dev.omar.checkout.Fixtures.BOOK_PRICE;
import static dev.omar.checkout.Fixtures.GRACE;
import static dev.omar.checkout.Fixtures.MUG;
import static dev.omar.checkout.Fixtures.MUG_PRICE;
import static dev.omar.checkout.Fixtures.NOW;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import dev.omar.checkout.domain.CustomerId;
import dev.omar.checkout.domain.Order;
import dev.omar.checkout.domain.OrderId;
import dev.omar.checkout.domain.OrderLine;
import dev.omar.checkout.port.DuplicateOrderException;
import dev.omar.checkout.port.OrderRepository;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * Contract tests: one suite of behavioural tests, run against every implementation. A fake is
 * only as good as its fidelity to the real thing; running both through the same contract is
 * what stops them drifting apart.
 */
public abstract class OrderRepositoryContract {

    private OrderRepository repository;

    /** A fresh, empty repository for each test. */
    protected abstract OrderRepository newRepository();

    @BeforeEach
    void createRepository() {
        repository = newRepository();
    }

    protected static Order order(String id, CustomerId customer) {
        return new Order(new OrderId(id), customer,
                List.of(new OrderLine(BOOK, 2, BOOK_PRICE), new OrderLine(MUG, 1, MUG_PRICE)), NOW, "tx-" + id);
    }

    @Test
    void savedOrderCanBeFoundByIdWithAllItsFields() {
        Order order = order("ORD-1", ADA);

        repository.save(order);

        assertEquals(Optional.of(order), repository.findById(order.id()));
    }

    @Test
    void unknownIdIsEmpty() {
        assertEquals(Optional.empty(), repository.findById(new OrderId("nope")));
    }

    @Test
    void ordersByCustomerAreFilteredAndKeepSaveOrder() {
        Order first = order("ORD-1", ADA);
        Order other = order("ORD-2", GRACE);
        Order second = order("ORD-3", ADA);
        repository.save(first);
        repository.save(other);
        repository.save(second);

        assertEquals(List.of(first, second), repository.findByCustomer(ADA));
        assertEquals(List.of(), repository.findByCustomer(new CustomerId("nobody")));
    }

    @Test
    void savingTheSameIdTwiceIsRejected() {
        repository.save(order("ORD-1", ADA));

        assertThrows(DuplicateOrderException.class, () -> repository.save(order("ORD-1", GRACE)));
        assertEquals(List.of(), repository.findByCustomer(GRACE));
    }

    @Test
    void freeTextFieldsRoundTripExactly() {
        Order awkward = new Order(new OrderId("ORD|7,x:y"), new CustomerId("o'brien | ünïcode"),
                List.of(new OrderLine(BOOK, 1, BOOK_PRICE)), NOW, "tx:with|separators,%20");

        repository.save(awkward);

        assertEquals(Optional.of(awkward), repository.findById(awkward.id()));
    }
}
