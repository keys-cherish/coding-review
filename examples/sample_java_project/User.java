package com.example.demo;

import java.util.*;
import java.util.List;
import java.io.IOException;

public class user {
    private static final int max = 999;
    public static int Y = 100;
    private int age;
    private String name;

    public user(String n, int a) {
        this.name = n;
        this.age = a;
    }

    public String CheckAge(int score) {
        if(score > 80) {
            if(score > 90) {
                return "A";
            } else {
                return "B";
            }
        } else if(score > 70) {
            return "C";
        } else if(score > 60) {
            return "D";
        }
        return "F";
    }

    public void doSomething() {
        try {
            int x = 1;
            String s = name + age;
        } catch (Exception e) {
        }
    }
}
