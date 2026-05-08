package com.example.demo;

/**
 * Calculator utility — 写得较规范的对照样本。
 */
public class Calculator {
    private static final int MAX_VALUE = 1000;
    private static final int MIN_VALUE = -1000;

    /**
     * Add two integers safely with bound checks.
     *
     * @param a the first number
     * @param b the second number
     * @return the bounded sum
     */
    public int safeAdd(int a, int b) {
        int result = a + b;
        if (result > MAX_VALUE) {
            return MAX_VALUE;
        }
        if (result < MIN_VALUE) {
            return MIN_VALUE;
        }
        return result;
    }

    /**
     * Divide with default fallback when denominator is zero.
     *
     * @param numerator the dividend
     * @param denominator the divisor
     * @param fallback fallback value when denominator is zero
     * @return the division result or fallback
     */
    public double safeDivide(double numerator, double denominator, double fallback) {
        if (denominator == 0) {
            return fallback;
        }
        return numerator / denominator;
    }
}
