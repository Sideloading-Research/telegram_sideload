from typing import List, Union


def to_int_sizes(values: List[Union[int, str]]) -> List[int]:
    """Convert a list of ints/decimal strings to ints.

    Raises ValueError if a value is negative or not an integer string.
    """
    sizes: List[int] = []
    for value in values:
        if isinstance(value, int):
            sizes.append(value)
        elif isinstance(value, str):
            stripped = value.strip()
            size = int(stripped)
            sizes.append(size)
        else:
            raise TypeError(f"Unsupported entry type: {type(value)}")

    # Validate non-negative sizes
    has_negative7 = False
    for size in sizes:
        if size < 0:
            has_negative7 = True
            break

    if has_negative7:
        raise ValueError("Sizes must be non-negative integers")

    return sizes


def validate_items_fit_in_box(sizes: List[int], capacity: int) -> None:
    """Ensure every item size is <= capacity and capacity is positive."""
    capacity_valid7 = isinstance(capacity, int) and capacity > 0
    if not capacity_valid7:
        raise ValueError("max_box_size must be a positive integer")

    too_large7 = False
    bad_item_ind = None
    for size in sizes:
        if size > capacity:
            too_large7 = True
            bad_item_ind = sizes.index(size)
            break

    if too_large7:
        raise ValueError(f"Too large! Ind: {bad_item_ind}, Val: {sizes[bad_item_ind]}")


def sort_sizes_descending(sizes: List[int]) -> List[int]:
    """Return a new list of sizes sorted in non-increasing order."""
    sorted_sizes = sorted(sizes, reverse=True)
    return sorted_sizes


def first_fit_decreasing_pack(sizes: List[int], capacity: int) -> List[List[int]]:
    """Pack items using First-Fit Decreasing. Returns list of boxes (lists of sizes).

    Guarantees: no box sum exceeds capacity.
    """
    boxes: List[List[int]] = []
    remaining_capacities: List[int] = []

    ordered = sort_sizes_descending(sizes)

    for size in ordered:
        placed7 = False
        for idx in range(len(remaining_capacities)):
            fits7 = remaining_capacities[idx] >= size
            if fits7:
                boxes[idx].append(size)
                remaining_capacities[idx] = remaining_capacities[idx] - size
                placed7 = True
                break

        if not placed7:
            boxes.append([size])
            remaining_capacities.append(capacity - size)

    return boxes


def pack_into_boxes(values: List[Union[int, str]], capacity: int) -> List[List[int]]:
    """High-level wrapper: convert, validate, and pack with FFD."""
    sizes = to_int_sizes(values)
    validate_items_fit_in_box(sizes, capacity)
    boxes = first_fit_decreasing_pack(sizes, capacity)
    return boxes


def verify_packing(boxes: List[List[int]], capacity: int) -> bool:
    """Verify that no box exceeds capacity and capacity is positive.

    Returns True if valid; raises ValueError otherwise.
    """
    capacity_valid7 = isinstance(capacity, int) and capacity > 0
    if not capacity_valid7:
        raise ValueError("Capacity must be a positive integer")

    violation7 = False
    for b in boxes:
        total = 0
        for s in b:
            total = total + s
        if total > capacity:
            violation7 = True
            break

    if violation7:
        raise ValueError("Packing verification failed: box overfilled")

    return True


if __name__ == "__main__":

    max_box_size = 130

    entries = [
        24,
        1,
        4,
        120,
        78,
        10,
        42,
        13,
        99,
        52,
    ]
    packed = pack_into_boxes(entries, max_box_size)
    # Optional verification step in debug scenarios
    verify_packing(packed, max_box_size)
    print(f"Boxes used: {len(packed)}")
    for i, box in enumerate(packed, start=1):
        print(f"Box {i}: {box} (sum={sum(box)})")
