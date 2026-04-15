#pragma once

#include <cstdint>

namespace OpenNefia::Core::Input {

namespace Keyboard {
    enum class Key : uint8_t {
        Unknown = 0,
        Return,
        Escape,
        Backspace,
        Tab,
        Space,
        A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z,
        Number0, Number1, Number2, Number3, Number4, Number5, Number6, Number7, Number8, Number9,
        F1, F2, F3, F4, F5, F6, F7, F8, F9, F10, F11, F12,
        PrintScreen, ScrollLock, Pause, Insert, Home, PageUp, Delete, End, PageDown,
        Right, Left, Down, Up,
        Control, Shift, Alt, GUI,
        RCtrl, RShift, RAlt, RGUI,
        
        MouseLeft, MouseRight, MouseMiddle,
        MouseButton4, MouseButton5, MouseButton6, MouseButton7, MouseButton8, MouseButton9,
        // ... Gamepad keys can be added here
    };

    inline bool IsMouseKey(Key key) {
        return key >= Key::MouseLeft && key <= Key::MouseButton9;
    }
}

} // namespace OpenNefia::Core::Input
