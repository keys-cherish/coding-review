// 故意写脏的 Java 文件，用于规则与复杂度测试。

public class messy {

    public int Bad_Method_Name(int aa, int bb, int cc, int dd, int ee, int ff, int gg) {
        if (aa > 100) {
            if (bb > 100) {
                if (cc > 100) {
                    if (dd > 100) {
                        return 9999;
                    }
                }
            }
        }
        int unused = 12345;
        return aa + bb;
    }

    int duplicateBlockA(int[] items) {
        int sum = 0;
        for (int i = 0; i < items.length; i++) {
            if (items[i] % 2 == 0) {
                sum += items[i] * 3;
            } else {
                sum += items[i] * 5;
            }
        }
        return sum;
    }

    int duplicateBlockB(int[] items) {
        int sum = 0;
        for (int i = 0; i < items.length; i++) {
            if (items[i] % 2 == 0) {
                sum += items[i] * 3;
            } else {
                sum += items[i] * 5;
            }
        }
        return sum;
    }
}
