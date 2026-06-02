;; hymera.generic — defgeneric / defmethod + :before / :after / :self 方法組合
;;
;; 設計：docs/03_traverser_and_passes.md §1-2
;;       docs/decisions/0001-clos-style-method-combination.md
;; 對照 c-mera：CLOS 泛型函式（內建）
;;
;; 提供一個極簡的 CLOS 風格多重派發：
;;   - 依「位置參數的實際型別 tuple」派發
;;   - 標準方法組合：:before(全部, 最具體先) → primary(最具體一個) → :after(全部, 最不具體先)
;;   - :self 限定詞（c-mera 特有）：若存在 applicable 的 :self 方法則完全接管

(defclass GenericFunction []
  "一個泛型函式物件。methods 以 (qualifier, type-tuple) 為鍵。

  qualifier 為 None（primary）/ \":before\" / \":after\" / \":self\" 之一。"

  (defn __init__ [self name]
    (setv self.name name)
    (setv self.methods {})        ; (qualifier, type-tuple) -> fn
    (setv self._cache {}))         ; (qualifier, actual-types) -> [fn ...]（依 specificity 排序）

  (defn add-method [self qualifier types fn]
    (setv (get self.methods #(qualifier (tuple types))) fn)
    (.clear self._cache)           ; 方法表變動，清快取
    fn)

  ;; --- 派發核心 ---

  (defn _applicable? [self registered actual]
    "registered 的每個位置都是 actual 對應位置的（非嚴格）父類別。"
    (and (= (len registered) (len actual))
         (all (gfor #(r a) (zip registered actual)
                    (issubclass a r)))))

  (defn _specificity [self registered actual]
    "回傳 MRO 距離總和；越小越具體。"
    (sum (gfor #(r a) (zip registered actual)
               (.index (. a __mro__) r))))

  (defn _collect [self qualifier actual]
    "回傳所有 applicable 的方法，依 specificity 由最具體到最不具體排序。"
    (setv key #(qualifier actual))
    (when (in key self._cache)
      (return (get self._cache key)))
    (setv cands
      (lfor #(qt fn) (.items self.methods)
            :if (and (= (get qt 0) qualifier)
                     (._applicable? self (get qt 1) actual))
            #((get qt 1) fn)))
    (.sort cands :key (fn [c] (._specificity self (get c 0) actual)))
    (setv result (lfor #(_ fn) cands fn))
    (setv (get self._cache key) result)
    result)

  (defn __call__ [self #* args]
    (setv actual (tuple (gfor a args (type a))))

    ;; 1. :self —— 若有 applicable，最具體者完全接管
    (setv selfs (._collect self ":self" actual))
    (when selfs
      (return ((get selfs 0) #* args)))

    ;; 2. :before —— 全部，最具體先
    (for [m (._collect self ":before" actual)]
      (m #* args))

    ;; 3. primary —— 最具體一個
    (setv primaries (._collect self None actual))
    (setv result (when primaries ((get primaries 0) #* args)))

    ;; 4. :after —— 全部，最不具體先（reversed）
    (for [m (reversed (._collect self ":after" actual))]
      (m #* args))

    result))


;; --- 對外宏 ---

(defmacro defgeneric [name params]
  "(defgeneric traverse [traverser node])
   建立一個 GenericFunction 並綁到 name。params 目前僅作文件用途（不檢查 arity）。"
  `(setv ~name (hy.I.hymera/generic.GenericFunction ~(str name))))


(defmacro defmethod [name #* rest]
  "(defmethod NAME [:qualifier] ((var Type) ...) body...)

  qualifier 可省略（= primary），或為 :before / :after / :self。"
  (setv first (get rest 0))
  (setv has-qual (isinstance first hy.models.Keyword))
  (setv qualifier (if has-qual (+ ":" first.name) None))
  (setv params (if has-qual (get rest 1) (get rest 0)))
  (setv body   (if has-qual (cut rest 2 None) (cut rest 1 None)))
  ;; params 形如 ((tr Traverser) (n Node))
  (setv var-names (lfor p params (get p 0)))
  (setv types     (lfor p params (get p 1)))
  `(.add-method ~name ~qualifier
     [~@types]
     (fn [~@var-names] ~@body)))
