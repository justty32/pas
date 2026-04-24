;cm:cxx

(include <iostream>)
(include <vector>)

(defparameter *fields* '((int  id) (char name[32]) (double balance)))

(defmacro make-getters (struct-name fields)
  `(progn
     ,@(loop for f in fields collect
        (let* ( (type (first f))
                (name (second f))
                (fn-name (cintern (format nil "~a_get_~a" struct-name name)))
              )
          `(function ,fn-name ((,struct-name s)) -> ,type
            (return (pref s ,name))
            )
        )
      )
    )
)

(defparameter *zz* '(int aa))

(struct account (decl #.*fields*))

(make-getters account #.*fields*)

(defmacro buf-size () (* 16 2))

(let ((buf-size (buf-size)))
  (decl (
          (char buf[buf-size])
        )
  )
)

(function main ((int argc)(char **argv)) -> int
  (progn
    (decl ((int i = 0)))
    i++)
  (return 0))
