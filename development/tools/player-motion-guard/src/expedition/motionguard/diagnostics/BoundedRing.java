package expedition.motionguard.diagnostics;

import java.util.*;

public final class BoundedRing<T> {
    private final Object[] values;
    private int start, size;
    public BoundedRing(int capacity) {
        if (capacity < 1) throw new IllegalArgumentException("capacity");
        values = new Object[capacity];
    }
    public synchronized void add(T value) {
        if (size == values.length) { values[start] = value; start = (start + 1) % values.length; }
        else { values[(start + size) % values.length] = value; size++; }
    }
    @SuppressWarnings("unchecked")
    public synchronized List<T> snapshot() {
        List<T> copy = new ArrayList<>(size);
        for (int i = 0; i < size; i++) copy.add((T) values[(start + i) % values.length]);
        return List.copyOf(copy);
    }
    public synchronized int size() { return size; }
}
