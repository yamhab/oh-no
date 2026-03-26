import contextlib
import dataclasses
import enum
import random

import blessed
import wcwidth

MIN_WIDTH = 80
MIN_HEIGHT = 24

START_LOGO = """  ___   __        ____  _____         _
 .'   `.[  |      |_   \\|_   _|       | |
/  .-.  \\| |--.     |   \\ | |   .--.  | |
| |   | || .-. |    | |\\ \\| | / .'`\\ \\| |
\\  `-'  /| | | |   _| |_\\   |_| \\__. ||_|
 `.___.'[___]|__] |_____|\\____|'.__.' (_)"""

MIN_PLAYERS = 2
MAX_PLAYERS = 8

HAND_CARDS = 7


class Color(enum.IntEnum):
    RED = enum.auto()
    YELLOW = enum.auto()
    GREEN = enum.auto()
    BLUE = enum.auto()
    WILD = enum.auto()

    def render(self, term: blessed.Terminal) -> str:
        rendered = ""
        match self:
            case self.RED:
                rendered = term.red_reverse + "RED"
            case self.YELLOW:
                rendered = term.yellow_reverse + "YELLOW"
            case self.GREEN:
                rendered = term.green_reverse + "GREEN"
            case self.BLUE:
                rendered = term.blue_reverse + "BLUE"
            case self.WILD:
                rendered = term.magenta_reverse + "WILD"
        return rendered


class Type(enum.IntEnum):
    NUMBER = enum.auto()
    SKIP = enum.auto()
    REVERSE = enum.auto()
    DRAW_TWO = enum.auto()
    WILD = enum.auto()
    WILD_DRAW_FOUR = enum.auto()

    def render(self) -> str:
        rendered = ""
        match self:
            case self.SKIP:
                return "SKIP"
            case self.REVERSE:
                return "REVERSE"
            case self.DRAW_TWO:
                return "DRAW TWO"
            case self.WILD_DRAW_FOUR:
                return "DRAW FOUR"
        return rendered


@dataclasses.dataclass(order=True)
class Card:
    color: Color
    type: Type
    number: int | None = None

    def render(self, term: blessed.Terminal) -> str:
        if self.type == Type.NUMBER:
            return self.color.render(term) + " " + str(self.number) + term.normal
        if self.type == Type.WILD:
            return self.color.render(term) + term.normal
        return self.color.render(term) + " " + self.type.render() + term.normal

    def playable(self, last: Card) -> bool:
        return (
            self.type in {Type.WILD, Type.WILD_DRAW_FOUR}
            or self.type == last.type != Type.NUMBER
            or self.color == last.color
            or self.number == last.number is not None
        )


@dataclasses.dataclass
class Game:
    term: blessed.Terminal
    num: int = 0
    current: int = 0
    direction: int = 1
    deck: list[Card] = dataclasses.field(default_factory=list)
    hands: list[list[Card]] = dataclasses.field(default_factory=list)
    stack: list[Card] = dataclasses.field(default_factory=list)
    skip: bool = False
    draw: int = 0

    def play(self) -> None:
        if self.term.width < MIN_WIDTH or self.term.height < MIN_HEIGHT:
            print(
                f"Minimum terminal dimensions: {MIN_WIDTH}x{MIN_HEIGHT}\nCurrent terminal \
dimensions: {self.term.width}x{self.term.height}",
            )
            return

        with self.term.fullscreen():
            self.setup_players()
            self.setup_cards()

            for _ in range(self.num):
                print(self.term.clear() + self.term.center("~~~ PLAYER 1's TURN ~~~"))
                self.print_hand()
                self.choose_card()
                self.card_action()
                with self.term.cbreak(), self.term.hidden_cursor():
                    print("Press any key to continue... ")
                    self.term.inkey()

                while len(self.hands[self.current]) != 0:
                    self.turn()
                    with self.term.cbreak(), self.term.hidden_cursor():
                        print("Press any key to continue... ")
                        self.term.inkey()

                print(f"{self.term.clear()}Player {self.current + 1} wins!")

    def setup_players(self) -> None:
        print(self.term.clear() + "\n")
        for line in START_LOGO.splitlines():
            print(self.term.center(line))
        print("\n" + self.term.center("Press CTRL-C to exit at any time"))
        print(self.term.center("Welcome to Oh No! How many people will be playing (2-8)?"))

        while self.num < MIN_PLAYERS or self.num > MAX_PLAYERS:
            with contextlib.suppress(ValueError):
                self.num = int(self.center_input("> "))
            print(
                self.term.move_x(0) + self.term.move_up() + self.term.clear_eol(),
                end="",
            )

    def center_input(self, prompt: str) -> str:
        if prompt.isascii() and prompt.isprintable():
            text_width = len(prompt)
        else:
            text_width = wcwidth.width(prompt, control_codes="ignore")
        total_padding = max(0, self.term.width - text_width)
        left_pad = total_padding // 2 + (total_padding & self.term.width & 1) - 1
        return input(" " * left_pad + prompt)

    def setup_cards(self) -> None:
        for color in [Color.RED, Color.YELLOW, Color.GREEN, Color.BLUE]:
            self.deck.append(Card(color, Type.NUMBER, 0))
            for number in range(1, 10):
                self.deck.extend(Card(color, Type.NUMBER, number) for _ in range(2))
            self.deck.extend(Card(color, Type.SKIP) for _ in range(2))
            self.deck.extend(Card(color, Type.REVERSE) for _ in range(2))
            self.deck.extend(Card(color, Type.DRAW_TWO) for _ in range(2))
        self.deck.extend(Card(Color.WILD, Type.WILD) for _ in range(4))
        self.deck.extend(Card(Color.WILD, Type.WILD_DRAW_FOUR) for _ in range(4))
        random.shuffle(self.deck)

        for hand in range(self.num):
            self.hands.append(self.deck[-HAND_CARDS:])
            del self.deck[-HAND_CARDS:]
            self.hands[hand].sort()

    def print_hand(self, playable: list[int] | None = None) -> None:
        print("Here are the cards in your hand:")
        for i, card in enumerate(self.hands[self.current]):
            print(f"{i + 1}: {card.render(self.term)}")
        if len(self.stack) != 0:
            print(f"The last played card on the stack was a {self.stack[-1].render(self.term)}.")
        if playable:
            print("You may play one of the following cards from your hand:")
            for i, card in enumerate(playable):
                if i < len(playable) - 1:
                    print(card + 1, end=", ")
                else:
                    print(card + 1)

    def choose_card(self, playable: list[int] | None = None) -> None:
        while True:
            with contextlib.suppress(ValueError, IndexError):
                choice = int(input("Which card would you like to play? ")) - 1
                if not playable or choice in playable:
                    self.play_card(choice)
                    if len(self.hands[self.current]) == 1:
                        print("Oh No!")
                    break
            print(
                self.term.move_x(0) + self.term.move_up() + self.term.clear_eol(),
                end="",
            )

    def play_card(self, choice: int) -> None:
        self.stack.append(self.hands[self.current][choice])
        print("You play a " + self.hands[self.current][choice].render(self.term))
        del self.hands[self.current][choice]

    def card_action(self) -> None:
        last = self.stack[-1]
        match last.type:
            case Type.SKIP:
                self.skip = True
            case Type.REVERSE:
                self.direction *= -1
            case Type.DRAW_TWO:
                self.skip = True
                self.draw = 2
            case Type.WILD:
                self.choose_color()
            case Type.WILD_DRAW_FOUR:
                self.choose_color()
                self.skip = True
                self.draw = 4

    def choose_color(self) -> None:
        while True:
            match input("Which color would you like to switch to (R, Y, G, B)? ").lower():
                case "r":
                    self.stack[-1].color = Color.RED
                    break
                case "y":
                    self.stack[-1].color = Color.YELLOW
                    break
                case "g":
                    self.stack[-1].color = Color.GREEN
                    break
                case "b":
                    self.stack[-1].color = Color.BLUE
                    break
                case _:
                    print(
                        self.term.move_x(0) + self.term.move_up() + self.term.clear_eol(),
                        end="",
                    )

    def turn(self) -> None:
        self.rotate()
        print(self.term.clear() + self.term.center(f"~~~ PLAYER {self.current + 1}'s TURN ~~~"))

        for _ in range(self.draw):
            self.draw_card()
        self.draw = 0

        if self.skip:
            self.print_hand()
            print("Turn skipped")
            self.skip = False
            return

        playable = self.playable_cards()
        card_played = False
        if len(playable) == 0:
            print("You have no valid cards to play")
            self.draw_card()
            playable = self.playable_cards()
            if len(playable) == 1:
                self.print_hand(playable)
                self.choose_card(playable)
                card_played = True
            else:
                self.print_hand()
        else:
            self.print_hand(playable)
            self.choose_card(playable)
            card_played = True

        if card_played:
            self.card_action()

    def rotate(self) -> None:
        self.current += self.direction
        if self.current < 0:
            self.current += self.num
        else:
            self.current %= self.num

    def draw_card(self) -> None:
        card = self.deck.pop()
        print(f"You draw a {card.render(self.term)} from the deck")
        self.hands[self.current].append(card)
        self.hands[self.current].sort()

    def playable_cards(self) -> list[int]:
        playable = []
        for i, card in enumerate(self.hands[self.current]):
            if card.playable(self.stack[-1]):
                playable.append(i)
        return playable


def main() -> None:
    term = blessed.Terminal()
    game = Game(term)
    game.play()


if __name__ == "__main__":
    main()
