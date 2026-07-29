# Synthetic Dataset Inconsistencies

This document maps the three deliberately planted inconsistencies that the system should detect or flag.

## Inconsistency 1: Outdated Policy Reference

**Location:** `refunds.json`, record `REF-002`

**Details:**
- Field: `policy_version`
- Current value: `"2022-05-01"` (outdated)
- Expected current value: `"2024-01-01"`
- Impact: This refund was processed under an old policy that may have different rules for store credit

**How to detect:** Query refunds and look for `policy_version` older than 2024-01-01, or cross-reference with a policy registry (if one existed).

---

## Inconsistency 2: Duplicate Record

**Location:** `refunds.json`, both records with `id: "REF-003"`

**Details:**
- First REF-003: order_id `ORD-003`, customer `CUST-C789`, date `2024-01-19`
- Second REF-003: order_id `ORD-004`, customer `CUST-D012`, date `2024-01-21`
- Problem: Same ID assigned to two different refunds (second should be `REF-004`)

**How to detect:** Index refunds by ID and check for collisions, or notice during semantic search that two distinct refunds have the same identifier.

---

## Inconsistency 3: Missing Required Field

**Location:** `orders.json`, record `ORD-006`

**Details:**
- Field: `customer_id` (missing)
- Status: `"cancelled"`
- Other fields: All present (date, items, total, address, warehouse)
- Impact: Cannot fully reconcile refund, support ticket, or billing inquiry for this order

**How to detect:** Validate required fields on load (customer_id, order total, etc.); this order would fail schema validation unless lenient.

---

## Dataset Composition

| Type | File | Count | Records |
|------|------|-------|---------|
| Orders | `orders.json` | 6 | ORD-001 to ORD-006 |
| Refunds | `refunds.json` | 4 | REF-001, REF-002, REF-003 (×2) |
| Support Tickets | `support_tickets.json` | 4 | TKT-001 to TKT-004 |
| Supplier Quality Reports | `supplier_reports.json` | 3 | SUP-001 to SUP-003 |
| Warehouse Logs | `warehouse_logs.json` | 5 | WH-001 to WH-005 |
| **Total** | | **22** | |

---

## Example Multi-Hop Question

"Why did refunds spike on Jan 19-22?" should reveal:
- REF-001 (defective Wireless Mouse) - sourced from SUP-001 quality report
- REF-002 (wrong item shipped, outdated policy) - will flag policy inconsistency
- REF-003 (customer cancellation) - links to ORD-003
- REF-003 duplicate (damaged stand) - links to ORD-004 but has duplicate ID

The system should cite which records and note missing/problematic data.
