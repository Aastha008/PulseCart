package com.pulsecart.backend.repository;

import com.pulsecart.backend.entity.Inventory;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface InventoryRepository extends JpaRepository<Inventory, Long> {

    Optional<Inventory> findByProductId(Long productId);

    /**
     * Pessimistic write lock (SELECT ... FOR UPDATE) to ensure strict concurrency isolation
     * and completely prevent overselling during simultaneous checkout attempts.
     */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT i FROM Inventory i WHERE i.product.id = :productId")
    Optional<Inventory> findByProductIdForUpdate(@Param("productId") Long productId);

    /**
     * Atomic conditional stock decrement at the database level.
     * Returns 1 if stock was sufficient and decremented, 0 if insufficient.
     */
    @Modifying
    @Query("UPDATE Inventory i SET i.stock = i.stock - :quantity " +
           "WHERE i.product.id = :productId AND i.stock >= :quantity")
    int decrementStockIfSufficient(@Param("productId") Long productId, @Param("quantity") Integer quantity);

    /**
     * Atomic stock restoration for order cancellations.
     */
    @Modifying
    @Query("UPDATE Inventory i SET i.stock = i.stock + :quantity " +
           "WHERE i.product.id = :productId")
    int incrementStock(@Param("productId") Long productId, @Param("quantity") Integer quantity);
}
