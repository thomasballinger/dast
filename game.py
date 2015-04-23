game = """
(do
    (set obstacles (list 1 0 1 0 0 1 0 0))
    (fun draw-ball-at-mouse (do
        (display 1)
        (draw_ball (mousex) (mousey))))
    (fun jump y dy (do
        (display 'jump!')
        (if (< y 1)
            (do (display dy)
                20)
            dy)))
    (fun step-x x dx
        (+
            (if (> x (width))
                0
                x)
            dx))
    (fun step-y y dy
        (+ y dy))
    (fun gravity y dy
        (if (> y 0)
            (- dy .01)
            dy))
    (fun ground y
        (if (< y 1)
            0
            y))
    (fun draw-ob x
        (draw x (height) 200, 200, 200))
    (fun draw-obs (do
        (draw-ob 20)
        (draw-ob 60)
        (draw-ob 100)
        (draw-ob 180)))
    (fun mainloop x y dx dy (do
        (if (mousepressed?)
            (do
                (set dy (jump y dy))
                (display "yay")))
        (set x (step-x x dx))
        (set y (step-y y dy))
        (set y (ground y))
        (set dy (gravity y dy))
        (background 100 100 100)
        (draw-obs)
        (draw-ball x (- (height) y))
        (render)
        (mainloop x y dx dy)))
    (mainloop 0 0 1 0))
"""

if __name__ == '__main__':
    from gamelib import builtins, game_methods
    #from gen_iter import run
    from obj_iter import run
    builtins.update(game_methods())
    print(run(game))
