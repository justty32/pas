# 把 LISP/c 嵌入你的 Lisp 程式 (07)

本章說明如何在你自己的 Common Lisp 程式裡直接使用 LISP/c，把一個 **Lisp 列表**（data structure）傳進去，立刻拿到一個 **C 程式碼字串**，完全不需要任何中間檔案或子行程。

---

## 核心：`cof` 和 `c` 接受的是列表，不是字串

LISP/c 的翻譯函式操作的是普通的 Lisp **資料結構**。你傳進去的是一個 quoted list，拿到的是一個 `string`。

```lisp
(load "c.lisp")

;; 傳入一個 Lisp 列表，取得 C 字串
(cof '(var x int 10))
;;=> "int x=10"

(cof '(func add int ((a int) (b int))
        (return (+ a b))))
;;=> "int add(int a,int b){
;;      return ((a)+(b));
;;   }"
```

兩個主要的翻譯函式：

| 函式 | 定義位置 | 輸入 | 輸出 |
|------|---------|------|------|
| `cof` | `c.lisp:367` | 一個任意 Lisp 物件 | 對應的 C 字串 |
| `c`   | `c.lisp:267` | 一個或多個 Lisp 物件 | 所有翻譯結果用 `;\n\n` 串接 |

`c` 適合翻譯多個頂層宣告：

```lisp
(c '(header stdio)
   '(func add int ((a int) (b int))
       (return (+ a b)))
   '(main
       (var result int (@add 1 2))
       (@printf (str "%d\n") result)
       (return 0)))
;;=> "#include <stdio.h>;\n\nint add(...);\n\nint main(...){...}"
```

---

## 動態建構列表：quasiquote

真正的威力在於用 Lisp 的 quasiquote（`` ` ``）在執行時動態組裝列表，再傳給 `cof`。

### 基本範例：從變數產生函式

```lisp
(load "c.lisp")

(defun gen-getter (field-name type struct-name)
  "產生一個 getter 函式，例如 get_x(point *p) { return p->x; }"
  (cof `(func ,(intern (format nil "GET-~a" (string-upcase (string field-name))))
              ,type
              (((pt p) ,struct-name))
           (return (slot p ,field-name)))))

(gen-getter 'x 'float 'point)
;;=> "float get_x(point *p){
;;      return ((p)->x);
;;   }"

(gen-getter 'length 'int 'array)
;;=> "int get_length(array *p){
;;      return ((p)->length);
;;   }"
```

### 用迴圈產生多份程式碼

```lisp
;; 為多個型別產生同一個函式
(defun gen-clamp (type)
  (cof `(func ,(intern (format nil "CLAMP-~a" (string-upcase (string type))))
              ,type
              ((val ,type) (lo ,type) (hi ,type))
           (if (< val lo) (return lo))
           (if (> val hi) (return hi))
           (return val))))

;; 收集成一整份 C 程式碼
(defun gen-clamp-family (types)
  (format nil "~{~a~^~%~%~}" (mapcar #'gen-clamp types)))

(format t "~a~%" (gen-clamp-family '(int float double)))
```

輸出：
```c
int clamp_int(int val,int lo,int hi){
   if((val)<(lo)) {
      return lo;
   }
   if((val)>(hi)) {
      return hi;
   }
   return val;
}

float clamp_float(float val,float lo,float hi){
   ...
}

double clamp_double(double val,double lo,double hi){
   ...
}
```

### 用 `,@`（splicing）插入動態產生的子列表

```lisp
;; 根據欄位定義列表產生 struct
(defun gen-struct (name fields)
  "fields 是 ((field-name type) ...) 的列表"
  (cof `(struct ,name
           ,(mapcar #'(lambda (f) (list (car f) (cadr f))) fields))))

(gen-struct 'player '((x float) (y float) (hp int) (name (t* char))))
;;=> "struct player{
;;      float x;
;;      float y;
;;      int hp;
;;      char* name;
;;   }"
```

```lisp
;; 根據欄位列表產生初始化函式
(defun gen-init-func (struct-name fields)
  (let ((params (mapcar #'(lambda (f)
                            `(,(car f) ,(cadr f)))
                        fields))
        (assignments (mapcar #'(lambda (f)
                                 `(= (slot p ,(car f)) ,(car f)))
                             fields)))
    (cof `(func ,(intern (format nil "INIT-~a" (string-upcase (string struct-name))))
                void
                (((pt p) ,struct-name) ,@params)
             ,@assignments))))

(gen-init-func 'player '((x float) (y float) (hp int)))
;;=> "void init_player(player *p,float x,float y,int hp){
;;      ((p)->x)=(x);
;;      ((p)->y)=(y);
;;      ((p)->hp)=(hp);
;;   }"
```

---

## 一次翻譯多個宣告：`c` 函式

```lisp
(defun gen-point-module ()
  "產生完整的 point 模組（struct + 函式群）"
  (apply #'c
    `((header math)

      (struct point
        ((x float) (y float)))

      ,@(mapcar #'(lambda (field)
                    `(func ,(intern (format nil "POINT-GET-~a"
                                           (string-upcase (string field))))
                           float
                           (((pt p) point))
                        (return (slot p ,field))))
                '(x y))

      (func point-distance float (((pt a) point) ((pt b) point))
        (var dx float (- (slot b x) (slot a x)))
        (var dy float (- (slot b y) (slot a y)))
        (return (@sqrt (+ (* dx dx) (* dy dy))))))))

(format t "~a~%" (gen-point-module))
```

---

## 把翻譯結果寫入檔案或傳給 GCC

取得字串之後，你可以用標準 Lisp 函式處理它：

```lisp
(load "c.lisp")

;; 寫入 .c 檔
(defun emit-c-file (path &rest exprs)
  (let ((code (apply #'c exprs)))
    (with-open-file (s path :direction :output
                           :if-exists :supersede
                           :if-does-not-exist :create)
      (format s "~a" code))))

(emit-c-file "output.c"
  '(header stdio)
  '(main (@printf (str "hello\n")) (return 0)))

;; 直接傳給 gcc（不落地成 .c 檔）
(defun compile-exprs (out-name &rest exprs)
  (let ((code (apply #'c exprs)))
    (ext:run-shell-command
      (format nil "echo ~s | gcc -x c - -o ~a" code out-name))))
```

---

## 完整的程式碼產生器範例

以下是一個實際的例子：根據一份欄位規格，自動產生對應的 struct、constructor、getter/setter 函式：

```lisp
(load "c.lisp")

(defun generate-class (name fields)
  "根據 ((field type) ...) 規格，產生完整的 C struct + 函式群。
   回傳一個 C 程式碼字串。"
  (let* ((ptr-type   `(pt p))
         ;; struct 定義
         (struct-def `(struct ,name ,fields))
         ;; new_Foo() 建構函式
         (new-func
           `(func ,(intern (format nil "NEW-~a" (string-upcase (string name))))
                  (t* ,name)
                  ()
               (var (pt p) ,name (@malloc (@sizeof (struct ,name))))
               ,@(mapcar #'(lambda (f)
                             `(= (slot p ,(car f)) 0))
                         fields)
               (return p)))
         ;; free_Foo(p) 解構函式
         (free-func
           `(func ,(intern (format nil "FREE-~a" (string-upcase (string name))))
                  void
                  ((,ptr-type ,name))
               (@free p)))
         ;; 每個欄位的 getter 和 setter
         (accessors
           (mapcan
             #'(lambda (f)
                 (let ((fname (car f))
                       (ftype (cadr f)))
                   (list
                     ;; getter
                     `(func ,(intern (format nil "GET-~a-~a"
                                            (string-upcase (string name))
                                            (string-upcase (string fname))))
                            ,ftype
                            ((,ptr-type ,name))
                         (return (slot p ,fname)))
                     ;; setter
                     `(func ,(intern (format nil "SET-~a-~a"
                                            (string-upcase (string name))
                                            (string-upcase (string fname))))
                            void
                            ((,ptr-type ,name) (val ,ftype))
                         (= (slot p ,fname) val)))))
             fields)))
    ;; 把所有部分翻譯並串接
    (apply #'c `(,struct-def ,new-func ,free-func ,@accessors))))

;; 使用
(format t "~a~%" (generate-class 'vec3 '((x float) (y float) (z float))))
```

輸出（節錄）：
```c
struct vec3{
  float x;
  float y;
  float z;
}

vec3 *new_vec3(){
   vec3 *p=malloc(sizeof(struct vec3));
   ((p)->x)=(0);
   ((p)->y)=(0);
   ((p)->z)=(0);
   return p;
}

void free_vec3(vec3 *p){
   free(p);
}

float get_vec3_x(vec3 *p){
   return ((p)->x);
}

void set_vec3_x(vec3 *p,float val){
   ((p)->x)=(val);
}
...
```

---

## 注意：符號（symbol）大小寫

CLISP 預設會把所有 symbol 轉成大寫再處理（`'myvar` 在 Lisp 內部是 `MYVAR`），但 `c-strify`（`c.lisp:139`）會把它轉成全小寫的 C 識別字。所以：

```lisp
;; 這三種寫法在 cof 裡效果完全相同
(cof '(var myVar int))     ;;=> "int myvar"
(cof '(var MYVAR int))     ;;=> "int myvar"
(cof '(var my-var int))    ;;=> "int my_var"  ← 建議用這個
```

如果你用 `intern` 動態建立 symbol 名稱，要注意：

```lisp
;; 產生 foo_bar
(intern "FOO-BAR")   ;; 正確，CLISP 內部會是 FOO-BAR → c-strify → "foo_bar"
(intern "foo-bar")   ;; 也正確，因為 c-strify 會 downcase

;; 產生 FOOBAR（大寫常數）
(intern "!FOO-BAR")  ;; ← 正確，c-strify 遇到 ! 前綴會全大寫 → "FOO_BAR"
```

---

## 從 Python 或 shell 呼叫（次要用法）

如果你的主程式不是 Common Lisp，只能透過子行程使用 LISP/c，這時就需要傳字串。這種方式較慢（每次啟動 CLISP 需約 0.5–1 秒），請見 `06_batch_convert.md` 中的 shell 和 Makefile 方法。

Python 範例（把 S-expression 字串傳給 CLISP）：

```python
import subprocess, os

def lispc_translate(expr_str: str, lispc_dir: str = ".") -> str:
    """把一個 S-expression 字串翻譯成 C 程式碼字串"""
    lisp_cmd = f'(load "{lispc_dir}/c.lisp") (format t "~a" (c \'{expr_str})) (quit)'
    result = subprocess.run(
        ["clisp", "-q", "-x", lisp_cmd],
        capture_output=True, text=True, check=True,
    )
    return result.stdout

print(lispc_translate("(func add int ((a int) (b int)) (return (+ a b)))"))
```

> 如果你的主程式是 Common Lisp，請直接用上面的 `cof`/`c` 方式，完全不需要子行程。
