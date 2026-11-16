package dev.omar.checkout.contract;

import dev.omar.checkout.adapter.InMemoryOrderRepository;
import dev.omar.checkout.port.OrderRepository;
import org.junit.jupiter.api.DisplayName;

@DisplayName("Contract: InMemoryOrderRepository (fake)")
class InMemoryOrderRepositoryTest extends OrderRepositoryContract {

    @Override
    protected OrderRepository newRepository() {
        return new InMemoryOrderRepository();
    }
}
