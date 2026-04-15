; Copyright Jonathan Baca, 2016
; ============================================================
; c.lisp — LISP/c 翻譯引擎
;
; 整體結構：
;   1. 全域狀態初始化（雜湊表、輸出目標）
;   2. 基礎工具函式與巨集（字串、列表、符號命名）
;   3. 運算子產生器（binop / lredop / rredop）
;   4. cof / c-strify：核心翻譯分發器
;   5. C 語言關鍵字定義（cfuns 第一塊）
;   6. C++ 關鍵字定義（cfuns 第二塊）
;   7. 函式別名對（cfunc-syn macropairs）
;   8. C-synonym 表（CUDA / MPI / Pthreads / 基礎型別）
;   9. 檔案 I/O 與編譯入口函式
; ============================================================


; ── 1. 全域狀態 ─────────────────────────────────────────────
; 用 boundp 防止重複 load 時重設雜湊表（第一次載入才初始化）
(if (not (boundp '  ***C/LISP-SYSTEM-LOADED***))
 (progn
    (format t "Welcome to LISP/C. Loading constants...")
    (setf *lbrac* #\[)            ; 左方括號字元常數
    (setf *file-out* nil)         ; 目前輸出的 .c/.h 路徑；nil 表示不輸出到檔案
    (setf *exec-out* nil)         ; 可執行檔輸出路徑（給 compile-c 用）
    (setf *last-compiled* nil)    ; 上次編譯產生的暫存 .c 檔路徑（用來清理）
    (setf *c-synonyms* (make-hash-table))   ; syn/csyn 別名表：symbol → 任意值
    (setf *macrolist* (make-hash-table))    ; 已定義的 lispmacro 名稱集合（防重複）
    (setf *templatelist* (make-hash-table)))) ; 已定義的 template 名稱集合

(setf ***C/LISP-SYSTEM-LOADED*** T) ; 標記引擎已載入


; ── 2a. replace-fn ──────────────────────────────────────────
; 遞迴 AST 重寫器。用於 lisp/c-macro 展開時，
; 把宏體內對自身的遞迴呼叫（old-fn）替換成輔助函式名（new-fn），
; 讓遞迴宏能正常運作而不會無限展開。
(defun replace-fn (old-fn new-fn form)
(labels ((helper (form s)
    (if (atom form)
        (if (and s (eq form old-fn)) new-fn form)
        (if (null form)
            nil
            (if (atom (car form))
            (cond
            ((eq (car form) 'function)
                (cons 'function (helper (cdr form) t)))
            ((eq (car form) 'quote)
              (print (cadr form))
                `(quote ,(cadr form)))
            (t
                (cons (helper (car form) t)
                  (mapcar #'(lambda (x)
                  (helper x nil)) (cdr form)))))
              (cons (helper (car form) t)
                  (mapcar #'(lambda (x)
                  (helper x nil)) (cdr form))))))))
    (helper form t)))


; ── 2b. lisp/c-macro ────────────────────────────────────────
; 定義「遞迴 C 生成宏」的 Lisp 巨集。
; 展開後產生兩個函式：
;   - <nym>-background：真正的遞迴 Lisp 函式（使用 replace-fn 改寫自呼叫）
;   - <nym>-c          ：cdefun 包裝，呼叫 (c ...) 後回傳 C 字串
; 使用者在 .cl 檔中寫 (lisp/c-macro ...) 時，
; cof 看到它就會呼叫 lisp/c-macro-c，
; 再透過 eval 在執行期注冊這兩個函式。
(defmacro lisp/c-macro (nym llist &rest code)
    (let ((helper (addsyms nym '-background))
          (args (gensym)))
    `(progn
        (defun ,helper ,llist ,@(replace-fn nym helper code))
        (cdefun ,nym (&rest ,args) (c (apply #',helper ,args))))))

  ; (DEFMACRO LISP/C-MACRO (NYM LLIST &REST CODE)
  ;     (LET ((HELPER (GENSYM)))
  ;        `(DEFUN ,HELPER ,LLIST
  ;             ,@(REPLACE-FN NYM HELPER CODE))
  ;             (CDEFUN ,NYM (&REST ,ARGS)
  ;                     (C ,(APPLY HELPER ARGS)))))

; ── 2c. 列表工具 ────────────────────────────────────────────

; pairify：把扁平列表兩兩配對，例如 (a 1 b 2) → ((a 1) (b 2))
; 用於 macropairs 解析「名稱 值 名稱 值 ...」的格式
(defun pairify (xs)
  (if (null xs)
      nil
      (cons
        (list (car xs) (cadr xs))
        (pairify (cddr xs)))))

; macropairs：對一個巨集批次套用成對的引數
; 例如 (macropairs cfunc-syn foo bar baz qux)
; 展開成 (progn (cfunc-syn foo bar) (cfunc-syn baz qux))
(defmacro macropairs (m &rest xs)
  `(progn
     ,@(mapcar #'(lambda (x) `(,m ,@x)) (pairify xs))))

; ── 2d. 雜湊表操作巨集 ──────────────────────────────────────

; sethash：語法糖，(sethash key val hash) = (setf (gethash key hash) val)
(defmacro sethash (k v hash)
  `(setf (gethash ,k ,hash) ,v))

; inhash：檢查 key 是否存在於 hash，回傳第二個值（存在與否的布林）
(defmacro inhash (k hash)
  `(nth-value 1 (gethash ,k ,hash)))

; csyn：在 *c-synonyms* 表中設定一個翻譯別名（key → val）
; 翻譯時 cof 遇到 key 就改用 val 繼續翻譯
(defmacro csyn (k v)
  `(sethash ,k ,v *c-synonyms*))

; cunsyn：從 *c-synonyms* 移除一個別名（對應 LISP/c 的 unsyn）
(defmacro cunsyn (k)
  `(remhash ,k *c-synonyms*))


; ── 3. 檔案 I/O 與編譯輔助 ──────────────────────────────────

; write-out：把字串 str 附加寫入 *file-out* 指定的檔案
; 若 *file-out* 為 nil 則什麼都不做（純 REPL 預覽模式）
(defun write-out (str)
  (if *file-out*
      (with-open-file (stream *file-out* :direction :output :if-exists :append :if-does-not-exist :create)
	(format stream str))))

; change-file：設定目前輸出目標的檔名
; is-h 為真時副檔名用 .h，否則用 .c
; 對應 LISP/c 的 (change-file "mylib" t) → 輸出到 mylib.h
(defun change-file (file &optional is-h)
  (setf *exec-out* (c-strify file))
  (setf *file-out* (format nil "~a.~a" *exec-out* (if is-h #\h #\c))))

; change-exec：只設定可執行檔的輸出名稱（不含副檔名）
(defun change-exec (nym)
  (setf *exec-out* (c-strify nym)))

; compile-c：呼叫 gcc 把 *file-out* 編譯成 *exec-out*
(defun compile-c ()
  (ext:run-shell-command (format nil "gcc ~a -o ~a" *file-out* *exec-out*)))

; strof：把任何物件轉成字串（用 format nil "~a"）
(defun strof (x)
  (format nil "~a" x))


; ── 4. 列表與字串工具 ────────────────────────────────────────

; f/list：確保回傳一個列表；原子 x → (list x)，列表直接回傳
(defun f/list (x)
  (if (listp x) x (list x)))

; f/list/n：遞迴地把巢狀結構展開到第 n 層
; n=1 時等同 f/list；n=0 時不做任何事
(defun f/list/n (x &optional (n 1))
  (if (zerop n) x
      (if (eq 1 n) (f/list x)
          (mapcar #'(lambda (y) (f/list/n y (1- n))) (f/list x)))))

; decr：遞減某個 place（類似 --x）
(defmacro decr (x)
  `(setf ,x (1- ,x)))

; f/list//n：另一種巢狀 f/list 策略（較少使用）
(defun f/list//n (x &optional (n 1))
    (if (<= n 0) x
        (if (atom x)
            (list (f/list//n x (1- n)))
            (if (null (cdr x))
            (list (f/list//n (car x) (- n 2)))
            (list (f/list//n x (1- n)))))))


; strsof：把一個字串列表直接拼接（不加分隔）
(defun strsof (xs)
  (format nil "~{~a~}" xs))

; chs->str：字元列表 → 字串
(defun chs->str (x)
  (strsof x))

; str->chs：字串 → 字元列表
(defun str->chs (x)
  (loop for c across x collect c))

; replace-char：把字串中所有 before 字元換成 after 字元
; 用途：連字號 - 換底線 _（kebab-case → snake_case）
(defun replace-char (before after str)
  (chs->str (mapcar #'(lambda (x) (if (eq x before) after x)) (str->chs str))))

; numeric-string：判斷字串是否代表數字
(defun numeric-string (x)
  (ignore-errors (numberp (read-from-string x))))

; alphap：判斷字元是否為英文字母（用於判斷運算子開頭）
(defun alphap (x)
  (member (char-upcase x) (str->chs "ABCDEFGHIJKLMNOPQRSTUVWXYZ")))


; ── 5. c-strify：Lisp 符號 → C 識別字 ───────────────────────
; 這是整個引擎最核心的命名轉換函式。
; 規則（按優先順序）：
;   - 字串 → 直接回傳（不轉換）
;   - leavemostlyalone=t → 只做 downcase（給 operator 等用）
;   - 數字字串 → 直接回傳
;   - 前綴 ! → 去掉 ! 後全大寫且連字號→底線（例如 !max-size → MAX_SIZE）
;   - 前綴 = → 去掉 = 後做 CamelCase（例如 =my-class → MyClass）
;   - 前綴 - → 去掉 - 後做 lowerCamelCase（例如 -my-var → myVar）
;   - 其他 → 全小寫且連字號→底線（例如 my-var → my_var）
(defun c-strify (x &optional leavemostlyalone)
  (if (stringp x) x
      (let ((s (strof x)))
        (if leavemostlyalone
            (string-downcase s)
	(if (numeric-string s) s
	    (if (eq (char s 0) #\!) (replace-char #\- #\_ (cof (subseq s 1)))
         (if (eq (char s 0) #\=) (camelcase-c (cof (subseq s 1)))
         (if (eq (char s 0) #\-) (Lcamelcase-c (cof (subseq s 1)))
		(replace-char #\- #\_ (string-downcase s))))))))))

; sethash 再次定義（確保先於 c-strify 的呼叫可用）
(defmacro sethash (k v hash)
  `(setf (gethash ,k ,hash) ,v))

; addsyms：把多個符號/字串拼接後用 read-from-string 讀回 symbol
; 例如 (addsyms 'foo '-c) → foo-c
(defun addsyms (&rest syms)
  (read-from-string (strsof syms)))

; macn：對一個巨集形式展開 n 次（除錯用）
(defun macn (x &optional n)
  (def n 1)
  (if (zerop n) x (macn (macroexpand-1 x) (1- n))))

; def：「預設值」巨集，只在 a 為 nil 時才把 b 賦給 a
(defmacro def (a b) `(setf ,a (if ,a ,a ,b)))

; deff：對 place x 套用函式 f（就地修改）
(defmacro deff (x f)
  `(setf ,x (,f ,x)))


; ── 6. 函式別名工具 ──────────────────────────────────────────

; func-syn：為一個已有函式建立另一個名稱的別名函式
(defmacro func-syn (func syn)
  `(progn
     (defun ,syn (&rest args)
       (apply #',func args))
     (compile ',syn)))

; cfunc-syn：同 func-syn，但自動把兩個名稱都加上 -c 後綴
; 例如 (cfunc-syn slot ->) 讓 ->-c 等同於 slot-c
(defmacro cfunc-syn (func syn)
  `(func-syn ,(cnym func) ,(cnym syn)))

; func-syns：批次為一個函式建立多個別名
(defmacro func-syns (func syns &rest yns)
  (deff syns f/list)
  (setf syns (append syns yns))
  `(progn ,@(mapcar #'(lambda (syn) `(func-syn ,func ,syn)) syns)))

; cfunc-syns：批次 cfunc-syn
(defmacro cfunc-syns (func syns &rest yns)
  (deff syns f/list)
  (setf syns (append syns yns))
  `(progn ,@(mapcar #'(lambda (syn) `(cfunc-syn ,func ,syn)) syns)))

; un：就地取反（toggle boolean）
(defmacro un (x) `(setf ,x (not ,x)))

; cnym：把 LISP/c 關鍵字名稱轉成對應的 Lisp 翻譯函式名稱
; 例如 (cnym 'func) → func-c
; 這是所有 cdefun 與 cfunc-syn 的命名基礎
(defun cnym (nym)
  (nth-value 0 (addsyms nym '-c)))

; incr：遞增某個 place
(defmacro incr (x)
  `(setf ,x (1+ ,x)))

; cdefun：定義一個 LISP/c 翻譯函式（自動加 -c 後綴並立刻 compile）
; (cdefun foo (x) body) 等同於 (defun foo-c (x) body) + (compile 'foo-c)
; 這是整個引擎中最核心的定義宏：所有 C 關鍵字翻譯函式都用它建立
(defmacro cdefun (f args &body body)
  `(progn
     (defun ,(cnym f) ,args ,@body)
     (compile ',(cnym f))))


; ── 7. 運算子產生器 ──────────────────────────────────────────

; binop2：產生單一二元運算子的翻譯函式（兩個操作數）
; nlp/nrp 控制左/右是否加括號
(defmacro binop2 (oper &key nlp nrp nym)
  (def nym oper)
  (un nlp)
  (un nrp)
  (labels ((helper (a b) (if a `(format nil "(~a)" (cof ,b)) `(cof ,b))))
    `(cdefun ,nym (x y) (format nil "~a~a~a" ,(helper nlp 'x) ',oper ,(helper nrp 'y)))))

; lredop：左折疊運算子（多個操作數從左結合）
; 例如 (= a b c) → a=b=c（實際上是左結合的賦值）
(defmacro lredop (oper &key nym nparen)
  (def nym oper)
  (let ((lp (if nparen "" "(")) (rp (if nparen "" ")")))
    `(cdefun ,nym (&rest xs)
	     (if (null xs) nil
		 (if (= 1 (length xs))
		     (format nil "~a~a~a" ,lp (cof (car xs)) ,rp)
		     (format nil "~a~a~a~a~a~a~a"
               ,lp
                ,lp (cof (car xs)) ,rp
               ',oper
               (apply (function ,(cnym nym)) (cdr xs)) ,rp))))))

; rredop：右折疊運算子（多個操作數從右結合）
(defmacro rredop (oper &key nym nparen)
  (def nym oper)
  (let ((lp (if nparen "" "(")) (rp (if nparen "" ")")))
    `(cdefun ,nym (&rest xs)
	     (if (null xs) nil
		 (if (= 1 (length xs))
		     (format nil "~a~a~a" ,lp (cof (car xs)) ,rp)
		     (format nil "~a~a~a~a~a~a~a" ,lp (apply (function ,(cnym nym)) (butlast xs)) ',oper ,lp (cof (car (last xs))) ,rp ,rp))))))

; parenify：在字串外加一對括號
(defun parenify (x)
  (format nil "(~a)" x))

; binop：統一入口，根據 :l/:r/:nyms 分派到 lredop / rredop / binop2
; :nyms 可一次定義多個別名
(defmacro binop (oper &key nlp nrp nym nyms l r nparen)
  ;;; (format t "OPER:~a NYM:~a NYMS:~a NPAREN:~a~%" oper nym nyms nparen)
  (if nyms
      `(progn ,@(mapcar #'(lambda (x) `(binop ,oper :nlp ,(un nlp) :nrp ,(un nrp) :nym ,x :l l :r r :nparen ,nparen)) nyms))
      (if (or l r)
	  (if l `(lredop ,oper :nym ,nym :nparen ,nparen) `(rredop ,oper :nym ,nym :nparen ,nparen))
	  `(binop2 ,oper :nlp ,nlp :nrp ,nrp :nym ,nym))))

; pre / post / prepost / preposts / binops：前綴/後綴/雙向一元運算子的批次產生器
; 例如 (pre ++ :nym ++) 產生 ++-c = "++x"
;      (post ++ :nym +++) 產生 +++-c = "x++"
(defmacro pre (oper &key nym nparen)
  `(cdefun ,nym (x) (format nil "~a~a~a~a" ',oper ,(if nparen "" "(") (cof x) ,(if nparen "" ")") )))
(defmacro post (oper &key nym nparen)
  `(cdefun ,nym (x) (format nil "~a~a~a~a" ,(if nparen "" "(") (cof x) ,(if nparen "" ")") ',oper)))
(defmacro prepost (oper &key post nym nparen nyms)
  (setf nym (if nym nym oper))
  (if nyms
      `(progn ,@(mapcar #'(lambda (x) `(prepost ,oper :post ,post :nym ,x :nparen ,nparen)) nyms))
      (if post
	  `(post ,oper :nym ,nym :nparen ,nparen)
	  `(pre ,oper :nym ,nym :nparen ,nparen))))
(defmacro preposts (&rest opers)
  `(progn ,@(mapcar #'(lambda (oper) `(prepost ,@(f/list oper))) opers)))
(defmacro binops (&rest opers)
  `(progn ,@(mapcar #'(lambda (oper) `(binop ,@(f/list oper))) opers)))


; ── 8. 其他工具 ──────────────────────────────────────────────

; swap：交換兩個 place 的值（編譯期巨集）
(defmacro swap (a b)
  (let ((c (gensym)))
    `(let ((,c ,a))
       (setf ,a ,b)
       (setf ,b ,c)
       (setf ,c ,a))))

; cfun / cfuns：cdefun 的語法糖包裝，cfuns 可批次定義多個翻譯函式
(defmacro cfun (nym llisp &body body)
  `(cdefun ,nym ,llisp ,@body))

(defmacro cfuns (&body defs)
  `(progn ,@(mapcar #'(lambda (def) `(cfun ,@def)) defs)))

; c：頂層翻譯函式，翻譯一個或多個 S-expression，結果以 ";\n\n" 分隔
; cwf 和 c-whole-file 最終都透過這個函式輸出 C 程式碼
(defun c (&rest xs)
  (format nil "~{~a~^~(;~%~%~)~}" (mapcar #'cof xs)))

; pc：把翻譯結果印到標準輸出（REPL 除錯用）
(defun pc (&rest xs)
  (format t "~a" (apply #'c xs)))

; repeatnrepeatnrepeatn：重複字元或字串 n 次
; 例如 (repeatnrepeatnrepeatn #\* 3) → "***"
; 用於產生 **ptr、&&&addr 等多層指標/取址
(defun repeatnrepeatnrepeatn (x &optional (n 1))
  (format nil "~{~a~}"
          (loop for i from 1 to n collect x)))

; cwrite：把翻譯結果加上 ";\n" 後寫入 *file-out*
(defmacro cwrite (&rest xs)
  `(write-out (format nil "~a;~%" (c ,@xs))))

; symtrim：把符號的字串表示去掉前 n 個字元後讀回 symbol
; 例如 (symtrim '@printf 1) → printf（用於 @ 前綴解析）
(defun symtrim (x n)
  (read-from-string (subseq (strof x) n)))


; ── 9. 大小寫轉換工具 ────────────────────────────────────────

; capitalize-c：首字母大寫，其餘小寫
(defun capitalize-c (str)
  (format nil "~a~a"
          (string-upcase (char (strof str) 0))
          (string-downcase (subseq (strof str) 1))))

; uncapitalize-c：首字母小寫
(defun uncapitalize-c (str)
  (format nil "~a~a"
          (string-downcase (char (strof str) 0))
          (subseq (strof str) 1)))

; flatten：把任意深度的巢狀列表展平成單層列表
(defun flatten (xs)
  (if (atom xs) (list xs) (mapcan #'flatten xs)))

; divide-at：在列表中每次遇到 elem 就切分（回傳列表的列表）
(defun divide-at (seq elem)
  (labels ((helper (seq elem curr res)
           (if (null seq) (cons (reverse curr) res)
               (if (eq (car seq) elem)
                   (helper
                     (cdr seq) elem nil (cons (reverse curr) res))
                   (helper
                     (cdr seq) elem (cons (car seq) curr) res)))))
         (reverse (helper seq elem nil nil))))

; split-str：按字元 ch 切分字串，去掉空字串
(defun split-str (str ch)
  (remove-if #'(lambda (x) (eq (length x) 0))
             (mapcar #'chs->str (divide-at (str->chs str) ch))))

; lowercase-c / uppercase-c：全小寫 / 全大寫
(defun lowercase-c (&rest strs)
  (format nil "~{~a~}" (mapcar #'string-downcase (mapcar #'strof strs))))

(defun uppercase-c (&rest strs)
  (format nil "~{~a~}" (mapcar #'string-upcase (mapcar #'strof strs))))

; camelcase-c：把多個字串拼成 CamelCase（大寫開頭）
; 先按 - 和 _ 切分，再把每個詞首字母大寫
(defun camelcase-c (&rest strs)
  (setf strs
        (flatten (mapcan #'(lambda (x) (split-str x #\-)) (mapcar #'strof strs))))
  (setf strs
        (flatten (mapcan #'(lambda (x) (split-str x #\_)) (mapcar #'strof strs))))
  (format nil "~{~a~}" (mapcar #'capitalize-c strs)))

; dashify-c：把多個運算式用 - 連接
(defun dashify-c (&rest strs)
  (format nil "~{~a~^-~}" (mapcar #'cof strs)))

; lcamelcase-c：lowerCamelCase（第一個詞小寫，後面大寫）
(defun lcamelcase-c (&rest strs)
  (setf strs
        (flatten (mapcan #'(lambda (x) (split-str x #\-)) (mapcar #'strof strs))))
  (format nil "~a~{~a~}" (string-downcase (car strs)) (mapcar #'capitalize-c (cdr strs))))

; with-optional-first-arg：解析「可選的首個關鍵字引數」模式
; 若 args 的第一個元素屬於 possible-values，就把它取出作為 nym；否則用 default-value
(defmacro with-optional-first-arg (args nym default-value possible-values &body body)
  (let ((other (gensym)))
    `(let ((,nym (if (member (car ,args) ',possible-values)
                     (car ,args)
                     ',other)))
       (if (eq ,nym ',other)
          (setf ,nym ,default-value)
          (setf ,args (cdr ,args)))
       ,@body)))

; gensym-n：產生 n 個 gensym
(defun gensym-n (&optional (n 1))
  (loop for i from 1 to n collect (gensym)))

; bar：示範 with-optional-first-arg 的用法（測試函式）
(defun bar (&rest xs)
  (with-optional-first-arg xs atmos 'cloudy (cloudy sunny rainy)
      (with-optional-first-arg xs deg 0 (0 1 2 3 4 5)
      (list atmos deg xs))))

; fib：費氏數列（compile-time，示範巨集能力）
(defmacro fib (n)
  (if (< n 2) 1 `(+ (fib ,(1- n)) (fib ,(- n 2)))))

; macnx：遞迴展開巨集形式（除錯用）
(defun macnx (macro-form &optional (n 1))
  (if (zerop n)
      macro-form
      (if (listp macro-form)
          (if (atom (car macro-form))
              (if (equal (macroexpand-1 macro-form) macro-form)
                  (mapcar #'(lambda (x) (macnx x n)) macro-form)
                  (macnx (macroexpand-1 macro-form) (1- n)))
              (mapcar #'(lambda (x) (macnx x n)) macro-form))
          macro-form)))

; padleft：把列表左側補 item 直到長度達到 len
; 用於 lambda++* 把引數補到固定位置
(defun padleft (lst item len)
  (if (>= (length lst) len)
      lst
      (append (padleft lst item (1- len)) (list item))))


; ── 10. cof：核心翻譯分發器 ──────────────────────────────────
; cof 是整個引擎的心臟，把任何 Lisp 物件翻譯成 C 字串。
; 分發邏輯：
;   - nil        → "" （空字串）
;   - 原子（atom）：
;       若在 *c-synonyms* 中 → 遞迴 cof（同義詞替換）
;       否則 → c-strify（符號→C識別字）
;   - 列表，car 是原子：
;       若 car 長度 > 1 且無對應 <car>-c 函式 → 按首字元分派：
;         @  → call-c（函式呼叫）
;         [  → nth-c（陣列索引，前綴 [ 去掉 2 個字元）
;         ]  → arr-c（陣列宣告）
;         &  → addr-c（取址）
;         ^  → cast-c（強制轉型）
;         *  → ptr-c（解引用）
;         .  → mem-c（. 成員存取）
;         >  → slot-c（-> 指標成員存取）
;         =  → camelcase-c（CamelCase 命名）
;         %  → lcamelcase-c（lowerCamelCase）
;         -  → lcamelcase-c（同 %）
;         其他 → 直接呼叫 <car>-c
;       若有對應 <car>-c 函式 → 直接呼叫
;   - 列表，car 是列表 → 把整個列表用 ";\n" 連接（多語句）
(defun cof (x)
  (if (null x)
      ""
      (if (atom x)
          (if (inhash x *c-synonyms*)
              (cof (gethash x *c-synonyms*))
              (c-strify x))
          (if (atom (car x))
              (if (and
                    (> (length (strof (car x))) 1)
                    (not (fboundp (cnym (car x)))))
                    (case (char (strof (car x)) 0)
                        (#\@ (apply #'call-c (cof (symtrim (car x) 1)) (cdr x)))
                        (#\[ (apply #'nth-c (cof (symtrim (car x) 2)) (cdr x)))
                        (#\] (apply #'arr-c (cof (symtrim (car x) 1)) (cdr x)))
                        (#\& (apply #'addr-c (cof (symtrim (car x) 1)) (cdr x)))
                        (#\^ (apply #'cast-c (cof (symtrim (car x) 1)) (cdr x)))
                        (#\* (apply #'ptr-c (cof (symtrim (car x) 1)) (cdr x)))
                        (#\. (apply #'mem-c (cof (symtrim (car x) 1)) (cdr x)))
                        (#\> (apply #'slot-c (cof (symtrim (car x) 1)) (cdr x)))
                        (#\= (apply #'camelcase-c (strof (symtrim (car x) 1)) (mapcar #'strof (cdr x))))
                        (#\% (apply #'lcamelcase-c (strof (symtrim (car x) 1)) (mapcar #'strof (cdr x))))
                        (#\- (apply #'lcamelcase-c (strof (symtrim (car x) 1)) (mapcar #'strof (cdr x))))
                        (otherwise (apply (cnym (car x)) (cdr x))))
                  (apply (cnym (car x)) (cdr x)))
              (format nil "~{~a~^~(;~%~)~}" (mapcar #'cof x))))))

; cofy：就地把某個 place 的值透過 cof 翻譯（= (setf x (cof x))）
(defmacro cofy (x) `(setf ,x (cof ,x)))
; cofsy：就地把一個列表的每個元素都做 cof
(defmacro cofsy (x) `(setf ,x (mapcar #'cof (f/list ,x))))


; ── 11. replacify：模板替換引擎 ──────────────────────────────
; replacify：把 template 中所有等於 vars[i] 的原子換成 subs[i]
; 這是 template 機制的核心：(template swap (T) ...) 呼叫時
; 用 replacify 把 T 替換成實際型別
(defun replacify (vars subs template)
  (labels ((helper (v s temp)
	     (if (eq temp v) s
		 (if (atom temp) temp
		     (mapcar #'(lambda (x) (helper v s x)) temp)))))
    (if (null vars) template
	(replacify (cdr vars) (cdr subs) (helper (car vars) (car subs) template)))))

; replacify-lambda：產生一個 lambda，呼叫時自動做 replacify
; 用於 template 的實作（把模板本體做成閉包）
(defmacro replacify-lambda (vars template)
  (let ((varlist (loop for i from 1 to (length vars) collect (gensym))))
    `(lambda ,varlist (replacify ',vars (list ,@varlist) ',template))))


; ═══════════════════════════════════════════════════════════════
; ── 12. C 語言關鍵字定義（binops / preposts）─────────────────
; 以下用 binops / preposts 批次產生所有算術、邏輯、位元、
; 賦值、比較、移位運算子的翻譯函式。
; 每個 :nyms 列表中的名稱都成為可用的 LISP/c 關鍵字別名。
; ═══════════════════════════════════════════════════════════════
;; ## NOW DEFINE THE C LANGUAGE

; 賦值與比較運算子
(binops (=   :l t :nyms (= set let <- ":="))      ; 賦值，左折疊
        (!=  :l t :nyms (!= neq diff different))   ; 不等於
        (==  :r t :nyms (== eq same))              ; 等於
        (<   :r t :nyms (< lt))
        (>   :r t :nyms (> gt))
        (<=  :r t :nyms (<= leq le))
        (>=  :r t :nyms (>= geq ge))
        ; 邏輯運算
        (&&  :r t :nyms (&& and et und y))
        (&   :r t :nyms (& bit-and band .and bit-et bet .et bit-und bund .und bit-y by .y ))
        (&=  :l t :nyms (&= &-eq bit-and-eq band-eq .and-eq bit-et-eq bet-eq .et-eq bit-und-eq bund-eq
			    .und-eq bit-y-eq by-eq .y-eq &= bit-and= band= .and= bit-et= bet=
			    .et= bit-und= bund= .und= bit-y= by= .y= ))
        ("||":r t :nyms (or uel oder o))
        ("|" :r t :nyms (bit-or .or bor bit-uel .uel buel bit-oder .oder boder bit-o .o bo))
        ("|=":l t :nyms (bit-or-eq .or-eq bor-eq bit-uel-eq .uel-eq buel-eq bit-oder-eq
                                   .oder-eq boder-eq bit-o-eq .o-eq bo-eq bit-or= .or=
                                   bor= bit-uel= .uel= buel= bit-oder= .oder= boder= bit-o= .o= bo=))
        ; 算術運算
        (+   :r t :nyms (+ plus add sum))
        (+=  :l t :nyms (+= plus-eq add-eq sum-eq plus= add= sum=))
        (-   :r t :nyms (- minus subtract sub))
        (-=  :l t :nyms (-= minus-eq subtract-eq sub-eq minus= subtract= sub=))
        (*   :r t :nyms (* times product mul multiply))
        (*=  :l t :nyms (*= times-eq product-eq mul-eq multiply-eq times= product= mul= multiply=))
        (/   :r t :nyms (/ quotient ratio div divide))
        (/=  :l t :nyms (/= quotient-eq ratio-eq div-eq divide-eq quotient= ratio= div= divide=))
        (%   :r t :nyms (% modulo mod remainder))
        (%=  :l t :nyms (%-eq modulo-eq mod-eq remainder-eq %= modulo= mod= remainder=))
        ; 移位運算
        (<<  :r t :nyms (<< l-shift shift-left shl))
        (" << " :l t :nparen t :nym <<+) ;; C++ 串流輸出，無括號
        (" >> " :l t :nparen t :nym >>+) ;; C++ 串流輸入，無括號
        (= :l t :nparen t :nym =!)        ;; 無括號賦值
        (<<= :l t :nyms (<<= l-shift-eq shift-left-eq shl-eq l-shift= shift-left= shl=))
        (>>  :r t :nyms (>> r-shift shift-right shr))
        (>>= :l t :nyms (>>= r-shift-eq shift-right-eq shr-eq >>= r-shift= shift-right= shr=))
        )

; 前綴/後綴一元運算子
; ++ 前綴：++ inc +inc ...
; ++ 後綴：+++ pinc inc+ ...
; -- 前綴：-- dec -dec ...
; -- 後綴：--- pdec dec- ...
; neg：取負（-x）
; !：邏輯非
; ~：位元非
; arg*：解引用型別（用在型別宣告中）
(preposts (++ :post nil :nyms (++  inc +inc incr pre++ +1 ++n))
          (++ :post t   :nyms (+++ pinc inc+ pincr post++ 1+ n++))
          (-- :post nil :nyms (--  dec -dec decr pre-- -1 --n))
          (-- :post t   :nyms (--- pdec dec- pdecr post-- 1- n--))
          (-  :post nil :nyms (neg))
          (!  :post nil :nyms (! not un a flip))
          (~  :post nil :nyms (~ bit-not bit-un bit-a bit-flip))
          (*  :post t   :nyms (ptrtyp arg*) :nparen t))


; ═══════════════════════════════════════════════════════════════
; ── 13. C 語言翻譯函式（cfuns 第一塊）────────────────────────
; 以下所有 (cfun name args body) 都透過 cdefun 定義為 name-c，
; 可在 .cl 檔的 S-expression 中直接呼叫。
; ═══════════════════════════════════════════════════════════════
(cfuns
 ; arr-decl：陣列初始化列表 { a, b, c }
 (arr-decl (&rest xs)
     (format nil "{~{~a~^~(, ~)~}}" (mapcar #'cof xs)))

 ; struct-decl：具名 struct 初始化 (name){ a, b }
 (struct-decl (&optional nym &rest xs)
              (cofy nym)
	   (format nil "(~a){~{~a~^~(, ~)~}}" nym (mapcar #'cof xs)))

 ; sym/add：把多個符號拼接成一個 C 識別字
 ; 例如 (sym/add swap- int) → "swap_int"
 ; 常用於 template 中動態生成函式名稱
 (sym/add (&rest xs)
	  (cofsy xs)
	  (strsof xs))

 ; slot：指標成員存取 a->b->c
 ; (slot p x y) → "(p)->x->y"
 (slot (a &rest bs)
        (cofy a)
        (cofsy bs)
        (format nil "(~a)~a~{~a~^~(->~)~}" a (if bs "->" "") bs))

 ; mem：值成員存取 a.b.c
 ; (mem s x y) → "(s).x.y"
  (mem (a &rest bs)
        (cofy a)
        (cofsy bs)
        (format nil "(~a)~a~{~a~^.~}" a (if bs "." "") bs))

 ; typ*：型別加 n 個星號（指標型別）
 ; (typ* char) → "char*"，(typ* void 2) → "void**"
 (typ* (x &optional (n 1))
       (cofy x)
       (format nil "~a~{~a~}" x (loop for i from 1 to n collect #\*)))

 ; const：const 型別宣告
 ; (const x int 42) → "const int x=42"
 ; (const buf char*) → "const char* buf"（單引數時 type=nil）
 (const (&rest xs)
	(format nil "const ~a" (apply #'var-c
    (if (= 1 (length xs)) (list (car xs) nil) xs))))

 ; syn：在翻譯期設定別名（不輸出 C 程式碼）
 ; (syn byte unsigned-char) 後，後續 byte 翻譯為 unsigned_char
 (syn (a b)
      (progn
	(csyn a b) ""))

 ; unsyn：移除翻譯期別名
 (unsyn (a)
	(progn
	  (cunsyn a) ""))

 ; progn：把多個語句用 "; \n" 連接輸出（C 語言沒有 progn，這只是並排）
 (progn (&rest xs)
	(format nil "~{  ~a;~^~%~}" (mapcar #'cof xs)))

 ; ?：三元運算子 test ? ifyes : ifno
 (? (test ifyes ifno)
    (cofy test)
    (cofy ifyes)
    (cofy ifno)
    (format nil "(~a)?~a:(~a)" test ifyes ifno))

 ; if：C 的 if/else
 ; (if cond then) 或 (if cond then else)
 (if (test &optional ifyes ifno)
     (cofy test)
     (cofy ifyes)
     (format nil "if(~a) {~%   ~a;~%}~a"  test ifyes (if ifno (format nil "else{~%   ~a;~%}"(cof ifno)) "")))

 ; cond：多路 if/else if（類似 C 的 switch，但更靈活）
 ; (cond (test1 body1...) (test2 body2...))
 (cond (&rest pairs)
       (format nil "if(~a) {~{~%  ~a;~}~%}~{~a~}" (cof (caar pairs)) (mapcar #'cof (cdar pairs))
         (mapcar #'(lambda (pair) (format nil "else if(~a){~{~%   ~a;~}~%}"
            (cof (car pair)) (mapcar #'cof (cdr pair)))) (cdr pairs))))

 ; ifs：連續 if（不是 else if，每個都獨立）
 (ifs (&rest pairs)
       (format nil "if(~a) {~{~%  ~a;~}~%}~{~a~}" (cof (caar pairs)) (mapcar #'cof (cdar pairs))
         (mapcar #'(lambda (pair) (format nil "if(~a){~{~%   ~a;~}~%}"
            (cof (car pair)) (mapcar #'cof (cdr pair)))) (cdr pairs))))

 ; main：產生標準 main 函式簽名 int main(int argc, char **argv)
 (main (&rest body)
       (format nil "int main(int argc,char **argv)~a" (block-c body)))

 ; for：C 的 for 迴圈
 ; (for init-expr cond-expr step-expr body...)
 (for (a b c &rest lines)
      (cofy a) (cofy b) (cofy c)
      (format nil "for(~a;~a;~a)~a" a b c (block-c lines)))

 ; while：C 的 while 迴圈
 (while (test &rest lines)
   (cofy test)
   (format nil "while(~a) ~a" test (block-c lines)))

 ; do-while：C 的 do-while 迴圈
 (do-while (test &rest lines)
   (cofy test)
   (format nil "do~awhile(~a)" (block-c lines) test))

 ; switch：C 的 switch 語句
 ; (switch var (case1 body1...) (case2 body2...))
 (switch (var &rest pairs)
	 (cofy var)
	 (labels ((helper (pairs)
		    (format nil "~a:~%   ~a~%~a"
			    (cof (caar pairs))
			    (block-c (cdar pairs) NIL)
			    (if (cdr pairs)
				(helper (cdr pairs))
				""))))
	   (format nil "switch(~a){~a}" var (helper pairs))))

 ; addr：取址運算子 &x（可多層）
 ; (addr x) → "&(x)"，(addr x 2) → "&&(x)"
 (addr (x &optional (n 1))
       (cofy x)
       (format nil "~a(~a)" (repeatnrepeatnrepeatn #\& n) x))

 ; ptr：解引用運算子 *p（可多層）
 (ptr (x &optional (n 1))
      (format nil "~{~a~}(~a)" (loop for i from 1 to n collect #\*) (cof x)))

 ; pt：在變數名稱前加 * 號（用於宣告中的指標名稱）
 ; (pt p) → "*p"，(pt argv 2) → "**argv"
 (pt (x &optional (n 1))
     (format nil "~{~a~}~a" (loop for i from 1 to n collect #\*) (cof x)))

 ; nth：陣列索引存取 a[i][j]...
 ; (nth arr i) → "(arr)[i]"
 (nth (x &optional (n 0) &rest ns)
      (format nil "(~a)[~a]~a" (cof x) (cof n)
	      (if ns
		  (format nil "~{[~a]~}" (mapcar #'cof ns)) "")))

 ; arr：宣告時的陣列大小 a[n]
 ; (arr a 10) → "a[10]"（用在 var 的名稱位置）
 (arr (x &optional n &rest ns)
      (format nil "~a[~a]~a" (cof x) (cof n)
	      (if ns
		  (format nil "~{[~a]~}" (mapcar #'cof ns)) "")))

 ; call：函式呼叫 name(arg1, arg2, ...)
 ; 也是 @ 前綴的實作目標（cof 中 #\@ → call-c）
 (call (nym &rest args)
       (format nil "~a(~{~a~^,~})" (cof nym) (mapcar #'cof args)))

 ; cuda/call：CUDA kernel 呼叫 name<<<grid,block>>>(args)
 (cuda/call (nym ijk &rest args)
	    (cofy nym) (cofsy ijk)
	    (format nil "~a<<<~{~a~^,~}>>>(~{~a~^,~})" nym ijk (mapcar #'cof args)))

 ; str：C 字串字面量（加雙引號）
 ; (str "hello world") → "\"hello world\""
 (str (&rest x)
      (cofsy x)
      (format nil "\"~{~a~^ ~}\"" x))

 ; char：C 字元字面量（加單引號）
 (char (x)
      (cofy x)
      (format nil "'~a'" x))

 ; cast：強制型別轉換 ((type)(expr))
 ; (cast x float) → "((float)(x))"
 ; 也是 ^ 前綴的實作目標
 (cast (nym &optional (typ 'int) &rest typs)
       (if typs
	   (apply #'cast-c (cast-c nym typ) typs)
	   (format nil "((~a)(~a))" (cof typ) (cof nym))))

 ; var：變數宣告（核心）
 ; 語法：(var 名稱 型別 初始值 修飾子...)
 ; 修飾子（static / extern / constexpr 等）排在型別之前
 ; 例如：
 ;   (var x int 0)         → "int x=0"
 ;   (var x int 0 static)  → "static int x=0"
 ;   (var (arr buf 10) int) → "int buf[10]"
 (var (x &optional type init &rest modifiers)
      (cofy x)
      (cofy type)
      (format nil "~a~a~{~a~^,~}~a"
              (if modifiers
                  (format nil "~{~a ~}" (mapcar #'cof modifiers))
                  "")
              (if type (format nil "~a " type) "")
              (f/list x) (if init (format nil "=~a" (cof init)) "")))

 ; vars：把多個 var 宣告串在一起，用 inter 分隔（預設逗號）
 ; 用於函式參數列表、struct 成員列表
 (vars (x &optional (inter #\,) (newline t))
       (setf x (mapcar #'(lambda (y) (apply #'var-c (f/list y))) (f/list/n x 1)))
       (format nil (format nil "~~{~~a~~^~(~a~a~)~~}" inter (if newline #\Newline "")) x))

 ; varlist：同 vars，但用分號分隔（用於局部變數宣告序列）
 (varlist (args)
          (vars-c args #\;))

 ; struct：C struct 定義
 ; (struct point ((x int) (y int))) → "struct point{ int x; int y;}"
 ; 無成員時只輸出 "struct name"（前向宣告用）
 ; 同時設 *c-synonyms*[***curr-class***] = name，供 construct/destroy 用
 (struct (nym &optional vars)
   (cofy nym)
   (csyn '***curr-class*** nym)    ; 記錄目前正在定義的 struct 名稱
   (if vars
       (format nil "struct ~a{~%  ~a;~%}" nym (vars-c vars #\;))
       (format nil "struct ~a" nym)))

 ; union：C union（同 struct，不同關鍵字）
 (union (nym &optional vars)
   (cofy nym)
   (if vars
       (format nil "union ~a{~%  ~a;~%}" nym (vars-c vars #\;))
       (format nil "union ~a" nym)))

 ; block：產生 C 語言的 { ... } 區塊
 ; 特殊處理：
 ;   - lines 第一個元素若是 'const → 在 { 前加 " const "（C++ const 方法）
 ;   - lines 第一個元素若是 (-> type) → 在 { 前加 " -> type"（尾置返回型別）
 ; bracket=nil 時不加 {}（用於 switch case body 等）
 (block (&optional lines (bracket t))
      (let ((preq "")
            (unempty (and lines (not (equal '(nil) lines)))))
        (if (eq 'const (car lines))   ; C++ const 方法
            (progn
              (setf preq " const ")
              (setf lines (cdr lines))))
        (if (listp (car lines))
            (if (eq '-> (caar lines)) ; C++11 尾置返回型別
                (progn
                  (setf preq
                      (format nil "~a -> ~a" preq (cof (cadar lines))))
                  (setf lines (cdr lines)))))
   (format nil "~a~a~a~{   ~a~(;~%~)~}~a"
      preq
      (if bracket #\{ "")
      (if unempty #\Newline "")
      (if unempty
          (mapcar #'cof (f/list lines))
          ())
      (if bracket #\} "") )))

 ; func：C 函式定義或宣告
 ; (func name ret-type ((arg1 type1) ...) body...)
 ; 無 body 時只輸出宣告（前向宣告）
 (func (nym &optional typ vars &rest body)
       (cofy nym)
       (cofy typ)
       (format nil "~a ~a(~a)~a" typ nym (vars-c vars #\, nil)
	       (if body (block-c body) "")))

 ; inline：在任何運算式前加 "inline "
 ; (inline (func ...)) → "inline ret_type name(...){...}"
 (inline (arg)
         (format nil "inline ~a" (cof arg)))

 ; cuda/global：CUDA __global__ kernel 函式
 (cuda/global (&rest args)
        (format nil "__global__ ~a" (apply #'func-c args)))

 ; cuda/device：CUDA __device__ 函式
 (cuda/device (&rest args)
        (format nil "__device__ ~a" (apply #'func-c args)))

 ; funcarg：函式指標型別
 ; (funcarg callback void ((x int))) → "void(*callback)(int x)"
 (funcarg (nym typ &optional varforms)
	  (cofy nym)
    (cofy typ)
	  (cofsy varforms)
	  (format nil "~a(*~a)(~{~a~^,~})" typ nym varforms))

 ; return：return 語句
 ; (return x) → "return x"
 ; (return x y) → "return x; y"（多個值時加分號）
 (return (&optional x &rest ys)
   (cofy x)
	 (format nil "return ~a~a~{~^ ~a~}"
          x (if ys #\; "")
          (if ys (mapcar #'cof ys) ())))

 ; typedef：C 型別別名
 ; (typedef int my-int) → "typedef int my_int;\n"
 ; (typedef (struct point) point) → "typedef struct point point;\n"
 (typedef (x &optional y)
	  (cofy x)
	  (format nil "typedef ~a ~a;~%" x (if y (cof y) "")))

 ; enum：C enum 定義
 ; (enum color red green blue) → "enum color{red, green, blue};\n"
 (enum (nym &rest mems)
       (cofy nym)
       (cofsy mems)
       (format nil "enum ~a{~{~a~^~(, ~)~}};~%" nym mems))

 ; h-file：把名稱加上 .h 副檔名字串
 (h-file (nym)
	 (cofy nym)
	 (format nil "~a.h" nym))

 ; str/add：字串拼接（用 cof 翻譯後）
 (str/add (&rest xs)
          (format nil "~{~a~}" (cof xs)))

 ; include：產生 #include 指令
 ; local=nil（預設）→ <filename>；local=t → "filename"
 (include (filename &key local)
	  (cofy filename)
	  (format nil "#include ~a~a~a~%" (if local #\" #\<) filename (if local #\" #\>)))

 ; import：在翻譯期載入並執行另一個 .cl 檔
 ; 這是 LISP/c 的「模組」機制：被載入的 .cl 定義的 template/lispmacro 可在後續使用
 (import (filename)
	 (setf filename (if (stringp filename) filename (format nil "~a.cl" (cof filename))))
	 (progn (c-whole-file filename)) (format nil "/* ~a LOADED */" filename))

 ; macro：展開 C 巨集呼叫（有引數的 function-like macro）
 ; (macro MAX a b) → "MAX(a,b)"
 (macro (nym &rest xs)
	(cofy nym)
	(format nil "~a(~{~a~^,~})" nym (mapcar #'cof (f/list xs))))

 ; unsigned：在型別前加 "unsigned "
 (unsigned (x)
           (cofy x)
           (format nil "unsigned ~a" x))

 ; define：#define 常數巨集（只支援無參數形式）
 ; (define !max-size 1024) → "#define MAX_SIZE 1024\n"
 ; 帶參數的 macro 請用 (cpp "define MACRO(a,b) ...")
  (define (a b)
     (cofy a)
   (cofy b)
   (format nil "#define ~a ~a~%" a b))

 ; ifdef：⚠ 有 bug！format 字串中 ~% 未被插入 expr
 ; 產生 "#ifdef ~%" 而非 "#ifdef EXPR"
 ; 請改用 (cpp ifdef !name) 代替
 (ifdef (expr)
        (cofy expr)
      (format nil "#ifdef ~~%" expr))   ; BUG: expr 未插入

 ; ifndef：⚠ 同 ifdef 的 bug
 ; 請改用 (cpp ifndef !name) 代替
 (ifndef (expr)
        (cofy expr)
      (format nil "#ifndef ~~%" expr))  ; BUG: expr 未插入

 ; if#：#if 條件編譯（正常，expr 有插入）
 (if# (expr)
        (cofy expr)
      (format nil "#if ~a~%" expr))

 ; else#：⚠ 回傳字面字串 "#else~%" 而非 "#else\n"
 ; ~% 只在透過 write-out 路徑才展開，cwf/cof 會看到字面 ~%
 ; 請改用 (cpp else) 代替
 (else# ()
       "#else~%")    ; ~% 不展開問題

 ; endif：⚠ 同 else# 的問題
 ; 請改用 (cpp endif) 代替
 (endif ()
        "#endif~%")  ; ~% 不展開問題

 ; pragma：#pragma 指令（最通用）
 ; (pragma once) → "#pragma once"
 ; (pragma pack 1) → "#pragma pack 1"
 (pragma (&rest xs)
         (cofsy xs)
         (format nil "#pragma ~{~a~^ ~}" xs))

 ; paren：在運算式外加括號
 (paren (x)
	(cofy x)
	(format nil "(~a)" x))

 ; comment：C 區塊注解 /* ... */
 ; (comment 's "small") → 只有 /* small */
 ; (comment "big") → 加裝飾行（/*****\n/* big */\n*****/ ）
 (comment  (&rest xs)
           (let* ((small (eq (car xs) 's))
                  (s (format nil "/* ~{~a~^ ~} */~%" (mapcar #'cof (if small (cdr xs) xs))))
                  (v (if small "" (format nil "/**~a**/~%" (repeatnrepeatnrepeatn #\* (- (length s) 7))))))
	     (format nil "~%~a~a~a~%" v s v)))

 ; header：包含 .h 標頭檔（等同 #include <name.h>）
 ; (header stdio) → "#include <stdio.h>"
 (header (nym &key local)
	 (include-c (h-file-c nym) :local local))

 ; headers：批次包含多個 .h 標頭檔
 ; (headers stdio stdlib math) → 三行 #include
 (headers (&rest xs)
	  (format nil "~{~a~}" (mapcar #'(lambda (x) (apply #'header-c (f/list x))) xs)))

 ; cpp：任意前置處理器指令（最通用，無 ifdef bug）
 ; (cpp ifndef !mylib-h) → "#ifndef MYLIB_H"
 ; (cpp "define MAX(a,b) ((a)>(b)?(a):(b))") → "#define MAX(a,b) ..."
 (cpp (&rest xs)
      (cofsy xs)
      (format nil "#~{~a~^ ~}" xs))

 ; lisp：在翻譯期執行任意 Lisp 程式碼，把結果字串插入輸出
 ; 必須回傳字串；若回傳非字串則輸出空字串
  (lisp (x)
       (let ((s (eval x)))
           (if (stringp s) s "")))

 ; lispmacro：定義一個翻譯期 Lisp 巨集（直接寫 Lisp 邏輯，輸出 C 字串）
 ; 與 template 的差別：lispmacro 可以執行任意 Lisp（if/loop/遞迴），
 ; 但最終必須用 (c '(...)) 或 cof 產生 C 字串。
 ; 若名稱已在 *macrolist* 中且不是本系統定義的 → 報錯
 (lispmacro (f llist &rest body)
            (if (and
                  (fboundp (cnym f))
                  (not (inhash f *macrolist*)))
      (format nil "/**ERROR: \"~a\" ALREADY DEFINED.**/" f)
      (progn
        (eval `(cdefun ,f ,llist ,@body))    ; 動態定義翻譯函式
        (sethash f t *macrolist*)            ; 記錄已定義
        (format nil "/**DEFINED: \"~a\" (lispmacro)**/" f))))

 ; lisp/c-macro 的翻譯層包裝（在 .cl 中使用時觸發）
 ; 呼叫 Lisp 層的 lisp/c-macro 巨集來動態建立遞迴 C 生成宏
 (lisp/c-macro (nym llist &rest body)
      (progn
        (eval `(lisp/c-macro ,nym ,llist ,@body))
        (format nil "/**LISP/C MACRO \"~a\"**/" nym)))

 ; lambda：翻譯期 lambda（用 replacify-lambda 做參數替換）
 ; 等同於在翻譯時展開一個匿名模板
 (lambda (llist template &rest args)
  (cof (eval `(apply (replacify-lambda ,llist ,template) ',args))))

 ; template：定義可重用的 C 程式碼模板（文字替換型）
 ; (template swap (T) body) 定義後，(swap int) 把 T 替換成 int 並輸出
 ; 底層：replacify-lambda 做符號→值的替換，再透過 cof 翻譯
 (template (f vars template)
	     (progn (eval `(cdefun ,f (&rest args)
			    (cof
         (apply (replacify-lambda ,vars ,template)
                (mapcar #'cof args)))))
         (sethash f t *templatelist*)
         (format nil "/**DEFINED: \"~a\" (template)**/" f) ))

 ; templates：一個模板定義可批次展開多個型別
 ; (templates make-print (T) body) 後，(make-prints int long) 展開兩份
 (templates (f vars template)
            (progn
              (eval `(cdefun ,f (&rest argss)
			     (apply #'progn-c (mapcar #'cof (mapcar #'(lambda (args)
								(apply
								 (replacify-lambda ,vars ,template)
								 (mapcar #'cof (f/list args))))
							    argss))))) ""))

 ; cuda/dim3 及相關：CUDA 維度設定
 (cuda/dim3 (typ x y)
	    (cofy typ)
	    (cofy x)
	    (cofy y)
    (format nil "dim3 ~a(~a,~a)" typ x y))
 (cuda/dim/block (x y)
		 (cuda/dim3-c 'dim/block x y))
 (cuda/dim/grid (x y)
		(cuda/dim3-c 'dim/grid x y))

 ; cuda/shared：__shared__ 變數宣告
 (cuda/shared (&rest xs)
    (format nil "__shared__ ~a" (apply #'var-c xs)))

 ; repeat：重複輸出某個運算式 n 次（用空格分隔）
 (repeat (x &optional (n 1))
     (cofy x)
    (format nil "~{~a~^ ~}" (loop for i from 1 to n collect x)))

 ; funcall / apply：在翻譯期呼叫已定義的 LISP/c 翻譯函式
 ; 用於元程式設計（讓一個 lispmacro 呼叫另一個）
  (funcall (func &rest args)
    (apply (cnym func) args))
 (apply (func &rest args)
    (setf args (append (butlast args) (car (last args))))
    (apply (cnym func) args))

 ; mapcar / mapargs：在翻譯期批次套用某個翻譯函式到多個引數組
 (mapcar (&rest argss)
   (with-optional-first-arg argss brackets? nil (t nil)
      (let ((func (car argss)))
        (setf argss (cdr argss))
        (block-c (apply #'mapcar (cnym func) argss) brackets?))))
 (mapargs (&rest argss)
    (with-optional-first-arg argss brackets? nil (t nil)
      (let ((func (car argss)))
        (setf argss (cdr argss))
        (block-c
          (mapcar
            #'(lambda (args) (apply-c func args))
                 argss) brackets?))))

 ; car/cdr/cadr/... 系列：在翻譯期操作 Lisp 列表（元程式設計用）
 (car (&rest args)
  (car args))
 (cdr (&rest args)
  (cdr args))
 (cadr (&rest args)
  (cadr args))
 (cdar (&rest args)
  (cdar args))
 (cddr (&rest args)
  (cddr args))
 (caar (&rest args)
  (caar args))

 ; binop（LISP/c 層）：動態二元運算子，用引數指定運算子字串
 ; (binop "%" a b) → "(a)%(b)"（在 lispmacro 中動態生成運算）
 (binop (opr &rest xs)
    (cofsy xs)
    (format nil
            (format nil "(~~{(~~a)~~^~~(~a~~)~~})" opr) xs))

 ; funcall-if / apply-if：條件式翻譯期函式呼叫
 (funcall-if (test func &rest args)
      (if test
          (apply #'funcall-c func args)
          (strsof (mapcar #'cof args))))
 (apply-if (test func args)
      (if test
          (apply #'funcall-c func args)
          (strsof (mapcar #'cof args))))

 ; test-eq / test-not / test-and / test-or：翻譯期條件測試
 ; 用於 lispmacro 內部的邏輯判斷
 (test-eq (a b)
          (eq a b))
 (test-not (a)
           (not a))
 (test-and (&rest xs)
          (eval `(and ,@xs)))
 (test-or (&rest xs)
          (eval `(or ,@xs)))

 ; code-list：把多個 S-expression 翻譯成 C 字串的列表（不合併）
 (code-list (&rest xs)
            (mapcar #'cof xs))

 ; list：在翻譯期建立 Lisp 列表（給 lispmacro/lisp/c-macro 使用）
 (list (&rest xs) xs)
)


; ═══════════════════════════════════════════════════════════════
; ── 14. C++ 翻譯函式（cfuns 第二塊）──────────────────────────
; 以下是 C++ 專用的翻譯函式。
; ═══════════════════════════════════════════════════════════════
;; C++ Stuff
(cfuns
 ; hh-file：產生 .hh 副檔名字串（C++ 慣用標頭）
 (hh-file (nym)
   (cofy nym)
   (format nil "~a.hh" nym))

 ; header++：包含 C++ 標頭（不加 .h，例如 #include <iostream>）
 ; (header++ iostream) → "#include <iostream>"
 (header++ (nym &key local)
   (if local
       (include-c (hh-file-c nym) :local local)
       (include-c nym)))

 ; headers++：批次包含 C++ 標頭
 (headers++ (&rest xs)
    (format nil "~{~a~}" (mapcar #'(lambda (x) (apply #'header++-c (f/list x))) xs)))

 ; tridot：把名稱後加 ...（C++ 可變參數包展開）
 ; (tridot args) → "args..."
  (tridot (x)
          (cofy x)
          (format nil "~a..." x))

 ; struct++：C++ struct（可有成員函式和存取控制）
 ; 同時設 ***curr-class*** synonym
 (struct++ (&optional nym &rest xs)
      (cofy nym)
    (csyn '***curr-class*** nym)
      (format nil "struct ~a~a" nym (if xs (block-c xs) "")))

 ; virtual：虛擬函式宣告
 ; (virtual (func foo int ())) → "virtual int foo()"
 ; (virtual (func foo int ()) 0) → "virtual int foo() = 0"（純虛擬）
 (virtual (&optional x y)
      (cofy x)
      (format nil "virtual ~a~a" x
              (if y (format nil " = ~a" (cof y)) "")))

 ; deprecated：[[deprecated]] 屬性
 ; (deprecated (func old void ())) → "[[deprecated]] void old()"
 ; (deprecated (var x int) "use y") → "[[deprecated("use y")]] int x"
  (deprecated (&optional x &rest msg)
      (cofy x)
      (format nil "[[deprecated~a]] ~a"
          (if msg (format nil "(\"~{~a~^ ~}\")" (mapcar #'cof msg)) "")
          x))

 ; delete：C++ delete / delete[]
 ; (delete ptr) → "delete ptr"
 (delete (&optional x)
      (cofy x)
      (format nil "delete ~a" x))

 ; lambda++：C++ lambda 運算式
 ; 完整語法：(lambda++ capture-list params attribs ret body...)
 ; [] 捕獲列表用 [] 符號（空捕獲）或列表
 ; 例如 (lambda++ [x y] ((n int)) () int (return (+ n x)))
 ;      → "[x,y](int n) -> int{...}"
 (lambda++ (&optional capture-list params attribs ret &rest body)
           (if (eq capture-list '[])
               (setf capture-list ()))
           (setf capture-list (mapcar
                 #'(lambda (x) (if (atom x) (c-strify x t) (cof x))) (f/list capture-list)))
           (setf attribs (mapcar #'cof (f/list attribs)))
     (format nil "[~{~a~^,~}]~a~{~^ ~a~}~a~a"
             capture-list
             (if (or params attribs ret) (parenify (vars-c params #\, nil)) "")
             attribs
             (if ret
                 (format nil " -> ~a " (cof ret)) "")
             (block-c body)))

 ; lambda++*：lambda++ 的簡化版，只需引數列表和本體
 ; (lambda++* ((x int)) (return x)) → "[](int x){return x;}"
 (lambda++* (&optional args &rest body)
       (apply #'lambda++-c (append (padleft (f/list args) nil 4) body)))

 ; namespace：C++ 命名空間存取 a::b::c
 ; (namespace std string) → "std::string"
 (namespace (&rest terms)
      (cofsy terms)
      (format nil "~{~a~^~(::~)~}" terms))

 ; namespacedecl：命名空間定義區塊
 ; (namespacedecl myns (func foo void ())) → "namespace myns{void foo()}"
 (namespacedecl (nym &rest terms)
    (cofy nym)
     (format nil "namespace ~a~a" nym (block-c terms)))

 ; typ&：引用型別（在型別宣告中）
 ; (typ& int) → "int&"，(typ& int 2) → "int&&"（右值引用）
 ; (typ& int 1 const) → "int const&"
 (typ& (&optional nym (n 1) const)
      (cofy nym)
      (if (not (numberp n))
         (progn
           (setf n 1)
           (setf const 'const)))
      (format nil "~a~a~a" nym
              (if const (format nil " ~a" (cof const)) "")
              (repeatnrepeatnrepeatn #\& n)))

 ; ptr&：引用到指標（在變數名稱位置）
 (ptr& (&optional nym (n 1))
       (cofy nym)
       (format nil "~a~a" (repeatnrepeatnrepeatn #\& n) nym))

 ; typ[&] / ptr[&]：用括號括住引用符號（函式引用等特殊語法）
 (typ[&] (&optional nym (n 1))
      (cofy nym)
      (format nil "~a(~a)" nym (repeatnrepeatnrepeatn #\& n)))
 (ptr[&] (&optional nym (n 1))
       (cofy nym)
       (format nil "(~a)~a" (repeatnrepeatnrepeatn #\& n) nym))

 ; class：C++ class 定義
 ; 支援繼承：(class derived ((inherits public base)) ...)
 ; 同時設 ***curr-class*** synonym 供 construct/destroy 使用
 (class (&optional nym &rest terms)
   (cofy nym)
   (csyn '***curr-class*** nym)
   (if (listp (car terms))
       (if (member (caar terms) '(inherits inh))   ; 繼承列表
           (progn
             (setf nym (format nil "~a : ~{~a~^ ~}"
                             nym
                             (mapcar #'cof (cdar terms))))
             (setf terms (cdr terms)))))
   (format nil "class~a~a~a" (if nym " " "") nym (if terms (block-c terms) "")))

 ; protected / private / public：存取控制修飾
 (protected (&rest terms)
   (cofsy terms)
   (format nil "protected:~%~a" (block-c terms nil)))
 (private (&rest terms)
   (cofsy terms)
   (format nil "private:~%~a" (block-c terms nil)))
 (public (&rest terms)
   (cofsy terms)
   (format nil "public:~%~a" (block-c terms nil)))

 ; construct：C++ 建構子
 ; (cx ((x int)) ((x x)) body...) → "ClassName(int x) : x(x){...}"
 ; init-pairs 格式：((成員 初始值) ...) → ": 成員(初始值), ..."
 (construct (&optional args init-pairs &rest code)
   (format nil "~a(~a)~a~a"
           (cof '***curr-class***)
           (vars-c args)
           (if init-pairs
               (format nil " : ~{~a~^~(, ~)~}"
                   (mapcar #'(lambda (xs)
                       (format nil "~a(~a)"
                               (cof (car xs))
                               (if (cadr xs)
                                   (cof (cadr xs))
                                   (cof (car xs)))))
                     init-pairs))
               "")
           (if code (block-c code) "" )))

 ; destroy：C++ 解構子
 ; (dx () body...) → "~ClassName(){...}"
 (destroy (&optional args &rest  code)
   (format nil "~~~a(~a)~a"
           (cof '***curr-class***)
           (vars-c args)
           (if code (block-c code) "")))

 ; constructor / destructor：在 class 內部引用目前類別名稱
 ; constructor → "ClassName"，destructor → "~ClassName"
 (constructor ()
   (format nil "~a" (cof '***curr-class***)))
 (destructor ()
   (format nil "~~~a" (cof '***curr-class***)))

 ; suffix：為識別字加上後綴（用於使用者定義字面量）
 (suffix (x y)
   (format nil "~a~a" (cof x) (c-strify y)))

 ; operator：運算子重載定義
 ; (op + vec ((v (t& vec))) body...) → "vec operator+(vec& v){...}"
 ; 支援：
 ;   - 普通運算子：+, -, *, /,  ==, (), [] 等
 ;   - 後綴字面量：(op (s my-lit) ...)  → operator""_my_lit
 ;   - 命名空間運算子：(op (@ ns +) ...)
 ;   - const 方法：(op + vec (...) const body...)
 (operator (oper &optional typ args &rest code)
   (let ((opr "operator") (constif ""))
                 (if (listp oper)
               (if (member (car oper) '(s su suf suffix))
                   (setf oper (format nil "\"\"_~a" (c-strify (cadr oper))))))
           (cofy typ)
           (if (listp oper)
               (if (member (car oper) '(@ ns namespace n/c))
                   (progn
                     (setf opr
                           (apply
                             #'namespace-c
                             (append (butlast (cdr oper)) (list opr))))
                     (setf oper (car (last oper))))))
           (if (null oper) (setf oper "()"))
           (setf oper (c-strify oper t))
           (if (eq (car code) 'const)   ; const 方法
               (progn
                 (setf constif " const ")
                 (setf code (cdr code))))
     (format nil "~a ~a~a~a(~a)~a~a"
             typ
             opr
             (if (alphap (char (strof oper) 0)) " " "")  ; 字母運算子前加空格
             oper
             (vars-c args)
             constif
             (if code (block-c code) ""))))

 ; friend：friend 宣告
 ; (friend (func foo int ())) → "friend int foo()"
 (friend (code)
   (cofy code)
   (format nil "friend ~a" code))

 ; decltemp：C++ template<...> 宣告
 ; 單參數：(decltemp T typename (class foo ...))
 ;           → "template<typename T> class foo{...}"
 ; 多參數：(decltemp ((T typename) (N int)) (func foo T ()))
 ;           → "template<typename T,int N> T foo()"
 (decltemp (&optional var typ &rest code)
     (if (listp var)
         (progn
           (setf var (mapcar #'f/list var))
           (setf code (cons typ code)))
         (setf var (f/list/n (list (list var typ)))))
     (cofy typ)
     (setf var (format nil "~{~a~^,~}"
                         (mapcar #'(lambda (pair) (format nil "~{~a~^ ~}"  (reverse (mapcar #'cof pair)))) var)))
     (format nil "template ~a~{~^ ~a~}" (if (or typ var)
                     (format nil "<~a>" var) "<>")
             (if code (mapcar #'cof code) '(""))))

 ; temp：模板特化或具名模板呼叫 name<T1, T2, ...>
 ; (temp vector int) → "vector<int>"
 ; (temp static-cast float) → "static_cast<float>"（與 call 配合可做 C++ 轉型）
 (temp (&optional var &rest typs)
       (cofy var) (cofsy typs)
       (format nil "~a<~{~a~^,~}>" var typs))

 ; using：命名空間 using 指令
 ; (using std) → "using namespace std"
 ; 注意：只有命名空間形式；型別別名請用 usevar/use
 (using (namespace)
        (format nil "using namespace ~a" (cof namespace)))

 ; usevar：using 型別別名 using NewName = OldType
 ; (use foo-type SomeClass) → "using foo_type=SomeClass"
 ; 別名：use / uv
 (usevar (&rest args)
         (format nil "~a" (apply #'var-c (car args) 'using (cdr args))))

 ; comment++：C++ 單行注解 //
 (comment++ (&rest comments)
            (cofsy comments)
            (format nil "//~{~a~^ ~}" comments))

 ; new：C++ new 運算式
 ; (new (call MyClass 1 2)) → "new MyClass(1,2)"
 (new (&rest xs)
      (cofsy xs)
      (format nil "new ~{~a~}" xs))

 ; try/catch：C++ 例外處理
 ; (t/c (e std-exception) try-body catch-body)
 (try/catch (catch &optional trybody catchbody)
   (setf catch (apply #'var-c (f/list catch)))
       (format nil "try~acatch(~a)~a" (block-c (f/list trybody))
               catch (if catchbody (block-c (f/list catchbody)) "")))

 ; strlit：字串字面量（同 str，另一個名稱）
 (strlit (&rest xs)
         (format nil "~a" (apply #'str-c xs)))

 ; explicit：⚠ 有 bug！format 字串遺失 xs 引數
 ; (format nil "explicit ~{~a~}") 沒有傳入 xs
 ; 實際輸出 "explicit " 後面為空
 (explicit (&rest xs)
     (cofsy xs)
     (format nil "explicit ~{~a~}"))  ; BUG: xs 未傳入 format
)


; ═══════════════════════════════════════════════════════════════
; ── 15. 函式別名對（cfunc-syn）────────────────────────────────
; 以下用 macropairs cfunc-syn 批次建立「關鍵字別名」。
; 每一對 (原名 別名) 讓 cof 看到「別名」時等同於呼叫「原名-c」。
; ═══════════════════════════════════════════════════════════════
(macropairs cfunc-syn
func f{}             ; func 的大括號別名
funcarg arg{}        ; funcarg 別名
funcarg fa{}
namespace n/s        ; namespace 的斜線別名
namespace ns
namespace @          ; @ 作為命名空間存取
slot ->              ; -> 指標成員存取
mem .>               ; .> 值成員存取
typ* t*              ; 指標型別
typ& t&              ; 引用型別
typ[&] [t&]          ; 括號引用
typ[&] t[&]
typ[&] t&[]
ptr p*               ; 指標解引用名稱
ptr& p&
ptr[&] [p&]
ptr[&] p[&]
ptr[&] p&[]
ptr& var&
var v                ; var 縮寫
delete del           ; delete 縮寫
class c.             ; class 的點號別名
class d/c
operator op          ; operator 縮寫
operator opr
construct   cx       ; constructor 縮寫
constructor   cxr
destroy dx           ; destructor 縮寫
destructor dxr
virtual vxl          ; virtual 縮寫
virtual virt
virtual virt.
return r             ; return 縮寫
headers hh           ; headers 縮寫
headers++ h+
header h
typedef t/d          ; typedef 縮寫
nth n.               ; 陣列存取縮寫
nth no.
nth nn
arr ar
arr-decl {}s
main m               ; main 縮寫
while w
do-while d/w
for f
arr a.
char ch
str s.               ; 字串字面量縮寫
varlist v/l
switch sx
call c               ; call 縮寫
struct s{}
struct sx
struct-decl sd{}
struct-decl {}s
struct-decl s{}s
struct-decl {sd}
struct++ s{}+
struct++ s{+}
struct++ sx+
struct++ sx++
struct++ struct+
block b
define d#            ; #define 縮寫
pragma p#            ; #pragma 縮寫
public pu.
private pr.
protected px.
friend fr.
template tmplt       ; template 縮寫
template !!
templates !!!
template t.
templates t..
lispmacro l/m        ; lispmacro 縮寫
lispmacro !!l
lisp/c-macro l/c-macro
lisp/c-macro l/c/m
lisp/c-macro !!lc
camelcase camel      ; 命名轉換縮寫
lcamelcase lcamel
capitalize cap
uncapitalize !cap
lowercase lcase
uppercase ucase
dashify -ify
comment cmt          ; 注解縮寫
comment z
comment /*
comment++ cmt+
comment++ cmt++
comment++ z+
comment++ //
temp <>              ; 模板參數縮寫
decltemp <t>
decltemp t<>
<<+ <stream          ; C++ 串流運算子縮寫
<<+ <<stream
<<+ <stream<
<<+ stream<
<<+ stream<<
<<+ <<<
>>+ stream>
>>+ stream>>
>>+ >stream
>>+ >>stream
>>+ >>>
addr memloc          ; 取址縮寫
addr loc
try/catch t/c        ; try/catch 縮寫
using u.             ; using 縮寫
usevar uv            ; usevar 縮寫
usevar use
namespacedecl ns/d   ; 命名空間宣告縮寫
namespacedecl n/s/d
namespacedecl ns{}
namespacedecl n/s{}
tridot t---          ; ... 展開縮寫
tridot t...
tridot d...
tridot v...
lambda++ l++         ; C++ lambda 縮寫
lambda++ l+
lambda++ l[]
lambda++ lambda[]
lambda++ lambda+
lambda++* l++*
lambda++* l+*
lambda++* l*
lambda++* l[]*
lambda++* lambda[]*
lambda++* lambda+*
lambda++* lambda*

)


; ═══════════════════════════════════════════════════════════════
; ── 16. C-Synonym 表（csyn macropairs）────────────────────────
; 以下用 csyn 在 *c-synonyms* 雜湊表中設定翻譯期別名。
; 當 cof 遇到這些 symbol 時，直接替換成對應的 C 字串。
; 注意：CUDA 和基礎別名用 quote (')；Pthreads 用 backquote (`)。
; ═══════════════════════════════════════════════════════════════

;; SYNONYMS

;;; CUDA STUFF ─────────────────────────────────────────────────
; CUDA runtime API 函式與常數的別名表
; 例如 cuda/malloc → "cudaMalloc"
(macropairs csyn
'cuda/malloc    "cudaMalloc"
'cuda/memcpy    "cudaMemcpy"
'cuda/free      "cudaFree"
'cuda/host->dev "cudaMemcpyHostToDevice"
'cuda/dev->host "cudaMemcpyDeviceToHost"
'cuda/dev/count "cudaDeviceCount"
'cuda/dev/set   "cudaSetDevice"
'cuda/dev/get   "cudaGetDevice"
'cuda/dev/props "cudaDeviceProperties"
'cuda/sync      "__syncthreads"
; 執行緒索引別名（threadIdx.x 等）
'block/idx      "blockIdx"
'block/idx/x    "blockIdx.x"
'block/idx/y    "blockIdx.y"
'block/idx/z    "blockIdx.z"
'thread/idx     "threadIdx"
'thread/idx/x   "threadIdx.x"
'thread/idx/y   "threadIdx.y"
'thread/idx/z   "threadIdx.z"
'block/dim      "blockDim"
'block/dim/x    "blockDim.x"
'block/dim/y    "blockDim.y"
'block/dim/z    "blockDim.z"
'grid/dim       "gridDim"
'grid/dim/x     "gridDim.x"
'grid/dim/y     "gridDim.y"
'grid/dim/z     "gridDim.z"
'dim/block      "dimBlock"
'dim/grid       "dimGrid"

;;; MPI STUFF ───────────────────────────────────────────────────
; MPI 錯誤碼、常數、型別、函式的完整別名表
; 例如 mpi/comm/world → "MPI_COMM_WORLD"
;      mpi/init       → "MPI_Init"
'mpi/success            "MPI_SUCCESS"
'mpi/err/buffer         "MPI_ERR_BUFFER"
'mpi/err/count          "MPI_ERR_COUNT"
'mpi/err/type           "MPI_ERR_TYPE"
'mpi/err/tag            "MPI_ERR_TAG"
'mpi/err/comm           "MPI_ERR_COMM"
'mpi/err/rank           "MPI_ERR_RANK"
'mpi/err/request        "MPI_ERR_REQUEST"
'mpi/err/root           "MPI_ERR_ROOT"
'mpi/err/group          "MPI_ERR_GROUP"
'mpi/err/op             "MPI_ERR_OP"
'mpi/err/topology       "MPI_ERR_TOPOLOGY"
'mpi/err/dims           "MPI_ERR_DIMS"
'mpi/err/arg            "MPI_ERR_ARG"
'mpi/err/unknown        "MPI_ERR_UNKNOWN"
'mpi/err/truncate       "MPI_ERR_TRUNCATE"
'mpi/err/other          "MPI_ERR_OTHER"
'mpi/err/intern         "MPI_ERR_INTERN"
'mpi/pending            "MPI_PENDING"
'mpi/err/in/status      "MPI_ERR_IN_STATUS"
'mpi/err/lastcode       "MPI_ERR_LASTCODE"
'mpi/bottom             "MPI_BOTTOM"
'mpi/proc/null          "MPI_PROC_NULL"
'mpi/any/source         "MPI_ANY_SOURCE"
'mpi/any/tag            "MPI_ANY_TAG"
'mpi/undefined          "MPI_UNDEFINED"
'mpi/bsend/overhead     "MPI_BSEND_OVERHEAD"
'mpi/keyval/invalid     "MPI_KEYVAL_INVALID"
'mpi/errors/are/fatal   "MPI_ERRORS_ARE_FATAL"
'mpi/errors/return      "MPI_ERRORS_RETURN"
'mpi/max/processor/name "MPI_MAX_PROCESSOR_NAME"
'mpi/max/error/string   "MPI_MAX_ERROR_STRING"
; MPI 型別
'mpi/char               "MPI_CHAR"
'mpi/short              "MPI_SHORT"
'mpi/int                "MPI_INT"
'mpi/long               "MPI_LONG"
'mpi/unsigned/char      "MPI_UNSIGNED_CHAR"
'mpi/unsigned/short     "MPI_UNSIGNED_SHORT"
'mpi/unsigned           "MPI_UNSIGNED"
'mpi/unsigned/long      "MPI_UNSIGNED_LONG"
'mpi/float              "MPI_FLOAT"
'mpi/double             "MPI_DOUBLE"
'mpi/long/double        "MPI_LONG_DOUBLE"
'mpi/byte               "MPI_BYTE"
'mpi/packed             "MPI_PACKED"
'mpi/float/int          "MPI_FLOAT_INT"
'mpi/double/int         "MPI_DOUBLE_INT"
'mpi/long/int           "MPI_LONG_INT"
'mpi/2int               "MPI_2INT"
'mpi/short/int          "MPI_SHORT_INT"
'mpi/long/double/int    "MPI_LONG_DOUBLE_INT"
'mpi/long/long/int      "MPI_LONG_LONG_INT"
'mpi/ub                 "MPI_UB"
'mpi/lb                 "MPI_LB"
; MPI 通訊子、群組常數
'mpi/comm/world         "MPI_COMM_WORLD"
'mpi/comm/self          "MPI_COMM_SELF"
'mpi/ident              "MPI_IDENT"
'mpi/congruent          "MPI_CONGRUENT"
'mpi/similar            "MPI_SIMILAR"
'mpi/unequal            "MPI_UNEQUAL"
'mpi/tag/ub             "MPI_TAG_UB"
'mpi/io                 "MPI_IO"
'mpi/host               "MPI_HOST"
'mpi/wtime/is/global    "MPI_WTIME_IS_GLOBAL"
; MPI 歸約運算
'mpi/max                "MPI_MAX"
'mpi/min                "MPI_MIN"
'mpi/sum                "MPI_SUM"
'mpi/prod               "MPI_PROD"
'mpi/maxloc             "MPI_MAXLOC"
'mpi/minloc             "MPI_MINLOC"
'mpi/band               "MPI_BAND"
'mpi/bor                "MPI_BOR"
'mpi/bxor               "MPI_BXOR"
'mpi/land               "MPI_LAND"
'mpi/lor                "MPI_LOR"
'mpi/lxor               "MPI_LXOR"
; MPI null 常數與物件型別
'mpi/group/null         "MPI_GROUP_NULL"
'mpi/comm/null          "MPI_COMM_NULL"
'mpi/datatype/null      "MPI_DATATYPE_NULL"
'mpi/request/null       "MPI_REQUEST_NULL"
'mpi/op/null            "MPI_OP_NULL"
'mpi/errhandler/null    "MPI_ERRHANDLER_NULL"
'mpi/group/empty        "MPI_GROUP_EMPTY"
'mpi/graph              "MPI_GRAPH"
'mpi/cart               "MPI_CART"
'mpi/aint               "MPI_Aint"
'mpi/status             "MPI_Status"
'mpi/group              "MPI_Group"
'mpi/comm               "MPI_Comm"
'mpi/datatype           "MPI_Datatype"
'mpi/request            "MPI_Request"
'mpi/op                 "MPI_Op"
'mpi/status/ignore      "MPI_STATUS_IGNORE"
'mpi/statuses/ignore    "MPI_STATUSES_IGNORE"
'mpi/copy/function      "MPI_Copy_function"
'mpi/delete/function    "MPI_Delete_function"
'mpi/handler/function   "MPI_Handler_function"
'mpi/user/function      "MPI_User_function"
; MPI 常用函式（有些重複，以最後一個定義為準）
'mpi/init               "MPI_Init"
'mpi/send               "MPI_Send"
'mpi/recv               "MPI_Recv"
'mpi/bcast              "MPI_Bcast"
'mpi/comm/size          "MPI_Comm_size"
'mpi/comm/rank          "MPI_Comm_rank"
'mpi/abort              "MPI_Abort"
'mpi/get/processor/name "MPI_Get_processor_name"
'mpi/get/version        "MPI_Get_version"
'mpi/initialized        "MPI_Initialized"
'mpi/wtime              "MPI_Wtime"
'mpi/wtick              "MPI_Wtick"
'mpi/finalize           "MPI_Finalize"
'mpi/open/port          "MPI_Open_port"
'mpi/comm/accept        "MPI_Comm_accept"
'mpi/comm/connect       "MPI_Comm_connect"
'mpi/scan               "MPI_Scan"
'mpi/allreduce          "MPI_Allreduce"
'mpi/comm/split         "MPI_Comm_split"
'mpi/isend              "MPI_Isend"
'mpi/irecv              "MPI_Irecv"
'mpi/wait               "MPI_Wait"
'mpi/test               "MPI_Test"
'mpi/init               "MPI_Init"
'mpi/finalize           "MPI_Finalize"
'mpi/comm/rank          "MPI_Comm_rank"
'mpi/comm/size          "MPI_Comm_size"
'mpi/get/count          "MPI_Get_count"
'mpi/type/extent        "MPI_Type_extent"
'mpi/type/struct        "MPI_Type_struct"
'mpi/scatter            "MPI_Scatter"
'mpi/gather             "MPI_Gather"
'mpi/sendrecv           "MPI_Sendrecv"
'mpi/sendrecv/replace   "MPI_Sendrecv_replace"
'mpi/group/rank         "MPI_Group_rank"
'mpi/group/size         "MPI_Group_size"
'mpi/comm/group         "MPI_Comm_group"
'mpi/group/free         "MPI_Group_free"
'mpi/group/incl         "MPI_Group_incl"
'mpi/comm/create        "MPI_Comm_create"
'mpi/wtime              "MPI_Wtime"
'mpi/get/processor/name "MPI_Get_processor_name"


;;; PTHREADS API ────────────────────────────────────────────────
; Pthreads 函式別名（注意：使用 backquote ` 而非 quote '）
; 例如 pthread/create → "pthread_create"
`pthread/create              "pthread_create"
`pthread/equal               "pthread_equal"
`pthread/exit                "pthread_exit"
`pthread/join                "pthread_join"
`pthread/self                "pthread_self"
`pthread/mutex/init          "pthread_mutex_init"
`pthread/mutex/destroy       "pthread_mutex_destroy"
`pthread/mutex/lock          "pthread_mutex_lock"
`pthread/mutex/trylock       "pthread_mutex_trylock"
`pthread/mutex/unlock        "pthread_mutex_unlock"
`pthread/cond/init           "pthread_cond_init"
`pthread/cond/destroy        "pthread_cond_destroy"
`pthread/cond/wait           "pthread_cond_wait"
`pthread/cond/timedwait      "pthread_cond_timedwait"
`pthread/cond/signal         "pthread_cond_signal"
`pthread/cond/broadcast      "pthread_cond_broadcast"
`pthread/once                "pthread_once"
`pthread/key/create          "pthread_key_create"
`pthread/key/delete          "pthread_key_delete"
`pthread/setspecific         "pthread_setspecific"
`pthread/getspecific         "pthread_getspecific"
`pthread/cleanup/push        "pthread_cleanup_push"
`pthread/cleanup/pop         "pthread_cleanup_pop"
`pthread/attr/init           "pthread_attr_init"
`pthread/attr/destroy        "pthread_attr_destroy"
`pthread/attr/getstacksize   "pthread_attr_getstacksize"
`pthread/attr/setstacksize   "pthread_attr_setstacksize"
`pthread/attr/getdetachstate "pthread_attr_getdetachstate"
`pthread/attr/setdetachstate "pthread_attr_setdetachstate"
`flockfile                   "flockfile"
`ftrylockfile                "ftrylockfile"
`funlockfile                 "funlockfile"
`getc/unlocked               "getc_unlocked"
`getchar/unlocked            "getchar_unlocked"
`putc/unlocked               "putc_unlocked"
`putc/unlocked               "putc_unlocked"
`pthread/detach              "pthread_detach"
; Pthreads 常數
'pthread/threads/max         "PTHREAD_THREADS_MAX"
'pthread/keys/max            "PTHREAD_KEYS_MAX"
'pthread/stack/min           "PTHREAD_STACK_MIN"
'pthread/create/detached     "PTHREAD_CREATE_DETACHED"
'pthread/create/joinable     "PTHREAD_CREATE_JOINABLE"

;;; BASIC STUFF ─────────────────────────────────────────────────
; 基礎型別與常數的便利別名
'null       "NULL"          ; C NULL 指標
'arg/c      "argc"          ; main 函式的引數個數
'arg/count  "argc"
'arg/v      "argv"          ; main 函式的引數陣列
'arg/values "argv"
'size/t     "size_t"        ; 標準大小型別
'integer    "int"           ; 語義型別別名
'integer+   "long"
'natural    "unsigned int"
'natural+   "unsigned long"
'real       "float"
'real+      "double"
'boolean    "char"
'stringc    "char*"
'---        "..."           ; C 可變引數 ...
'-#         "#"             ; 字串化運算子
'-##        "##"            ; token 拼接運算子
'-va-args-  "__VA_ARGS__"   ; 可變引數巨集展開
'-empty-    " "             ; 空格佔位
'--         " "
'-          "_"             ; 底線
'$          nil             ; 空符號（輸出空字串）
'int+ "long int"            ; 擴展整數型別別名
'int++ "long long int"
'double+ "long double"
'float+ "double"
'float++ "long double"
'template-params "template-params")


; ═══════════════════════════════════════════════════════════════
; ── 17. 檔案讀取與編譯入口 ────────────────────────────────────
; ═══════════════════════════════════════════════════════════════

; count-lines-in-file：計算檔案行數
(defun count-lines-in-file (filename)
  (let ((n 0))
    (with-open-file (stream filename :direction :input :if-does-not-exist nil)
      (if stream
	  (loop for line = (read-line stream nil 'done)
	     until (eq line 'done)
	     do (incr n))))
    n))

; read-whole-file：把整個檔案讀成一個字串（行之間用 \n 連接）
(defun read-whole-file (filename)
  (format nil "~{~a~^~%~}"
	  (with-open-file (stream filename :direction :input :if-does-not-exist nil)
            (if stream
                (loop for line = (read-line stream nil 'done)
		   until (eq line 'done)
		   collect line)))))

; stamp-time：產生目前時間字串（格式：秒/分/時/日/月/年）
(defun stamp-time ()
  (format nil "~{~a~^/~}"
    (reverse (multiple-value-list (get-decoded-time)))))

; c-whole-file：核心翻譯函式，讀取 .cl 檔並輸出翻譯後的 C 字串
; 流程：
;   1. read-whole-file 讀取全部內容
;   2. 用 read-from-string 逐個解析 S-expression（類似 read loop）
;   3. 把所有 S-expression 傳給 c 函式翻譯
;   4. 在輸出最前加上時間戳注解
(defun c-whole-file (filename)
  (let ((s (read-whole-file filename)) (result t) (n 0))
    (format nil "/*~a*/~%~a"
            (stamp-time)
      (apply #'c (loop while result collect
		    (progn
		      (multiple-value-setq (result n) (read-from-string s nil))
		      (setf s (subseq s n))
		      result))))))

; cwf（compile-whole-file preview）：翻譯 .cl 檔並印到標準輸出
; REPL 中最常用的預覽指令：(cwf "myfile.cl")
(defun cwf (filename)
  (format t "~a" (c-whole-file filename)))

; tempfilename：產生一個不衝突的隨機暫存檔名
(defun tempfilename (&optional extension)
  (labels ((genfilename () (strsof `(temp ,(random 1.0) ,extension))))
    (let ((filename (genfilename)))
      (loop while (probe-file filename) do
	   (setf filename (genfilename)))
      filename)))

; fileext：產生「名稱.副檔名」字串
(defun fileext (nym ext)
  (format nil "~a.~a" (c-strify nym) (c-strify ext)))

; c-cl-file：把 .cl 翻譯並寫入 .c 檔（最常用的一次性翻譯）
; (c-cl-file "main.cl" "main.c")
; 若不指定 fileout，自動用 filein 的基本名稱加 .c
(defun c-cl-file (filein &optional fileout)
  (let ((s (c-whole-file filein)) (temp nil))
    (if (null fileout)
        (progn
          (setf temp filein)
          (setf filein (fileext temp 'cl))
          (setf fileout (fileext temp 'c))))
    (if s
  (with-open-file (c-file-stream fileout :direction :output :if-does-not-exist :create)
    (format c-file-stream "~a" s)))))

; elapsed-time：把秒數格式化成 MM:SS 或 HH:MM:SS 字串（給 c-cl-file-continuous 用）
(defun elapsed-time (sec)
  (let* ((min (floor (/ (floor sec) 60)))
         (hr  (floor (/ min 60)))
         (day (floor (/ hr  24))))
    (setf sec (floor sec))
    (setf sec (mod sec 60))
    (setf min (mod min 60))
    (setf hr (mod hr 24))
    (format nil "~a~a~2,'0d:~2,'0d"
            (if (zerop day) "" (format nil "~a days, " day))
            (if (zerop hr) "" (format nil "~2,'0d:" hr))
            min sec)))

; c-cl-file-continuous：持續監看 .cl 檔，每 interval 秒重新翻譯一次
; ie=t 時忽略錯誤繼續執行；按 ^C 停止
(defun c-cl-file-continuous (filein &optional fileout ie (interval 1))
  (format t "Press ^C to stop.")
    (do ((i 0 (+ i interval))) (nil)
        (progn
          (format t "~&~a" (elapsed-time i))
          (if ie
              (ignore-errors (c-cl-file filein fileout))
              (c-cl-file filein fileout))
          (sleep interval))
        ))


; compile-cl-file：翻譯 .cl 並用 gcc/clang 等編譯成可執行檔
; 選項：
;   :fileout "out"      → 可執行檔輸出名稱（預設 "a.out"）
;   :tags "-std=c++17"  → 傳給編譯器的額外 flag
;   :libs "-lm -lpthread" → 連結庫
;   :c-file "my.c"      → 若指定則保留 .c 中間檔
;   :cc "g++"           → 指定編譯器（預設 "gcc"）
(defun compile-cl-file (filein &key fileout tags libs c-file cc)
  (def fileout "a.out")
  (def tags "")
  (def libs "")
  (def cc "gcc")
  (let ((c-code (c-whole-file filein)) (temp-file (if c-file c-file (tempfilename ".c"))))
    (format t "~a" c-file)
    (if (and *last-compiled* (not (eq *last-compiled* c-file))) (delete-file *last-compiled*))
    (with-open-file (c-file-stream temp-file :direction :output :if-does-not-exist :create)
      (format c-file-stream "~a" c-code))
    (format t "Running: ~a ~a ~a -o ~a ~a~%" cc tags temp-file fileout libs)
    (ext:run-shell-command (format nil "~a ~a ~a -o ~a ~a" cc tags temp-file fileout libs))
    (setf *last-compiled* temp-file)))

; compile-and-run-cl-file：翻譯、編譯並立刻執行
; :args 傳給可執行檔的命令列引數
(defun compile-and-run-cl-file (filein &key args fileout tags libs c-file cc)
  (def fileout "a.out")
  (compile-cl-file filein
		   :fileout fileout
		   :tags tags
		   :libs libs
		   :c-file c-file
		   :cc cc)
  (format t "Running: ./~a~{~^ ~a~}~%" fileout args)
  (ext:run-shell-command (format nil "./~a~{~^ ~a~}" fileout args)))


; ── 18. 編譯關鍵函式 ─────────────────────────────────────────
; 把最常呼叫的函式都做 native compile，提升執行效率
(compile 'write-out)
(compile 'change-file)
(compile 'change-exec)
(compile 'compile-c)
(compile 'strof)
(compile 'f/list)
(compile 'f/list/n)
(compile 'strsof)
(compile 'chs->str)
(compile 'str->chs)
(compile 'replace-char)
(compile 'c-strify)
(compile 'addsyms)
(compile 'macn)
(compile 'cnym)
(compile 'c)
(compile 'cof)
(compile 'read-whole-file)
(compile 'c-whole-file)
(compile 'cwf)
(compile 'tempfilename)
(compile 'compile-cl-file)
