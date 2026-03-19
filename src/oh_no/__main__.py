import dataclasses
import enum
import random


class Color(enum.IntEnum):
    RED = enum.auto()
    YELLOW = enum.auto()
    GREEN = enum.auto()
    BLUE = enum.auto()
    WILD = enum.auto()

    def __str__(self) -> str:
        color = ""
        match self:
            case self.RED:
                color = "RED"
            case self.YELLOW:
                color = "YELLOW"
            case self.GREEN:
                color = "GREEN"
            case self.BLUE:
                color = "BLUE"
            case self.WILD:
                color = "WILD"
        return color


class Type(enum.IntEnum):
    NUMBER = enum.auto()
    SKIP = enum.auto()
    REVERSE = enum.auto()
    DRAW_TWO = enum.auto()
    WILD = enum.auto()
    WILD_DRAW_FOUR = enum.auto()

    def __str__(self) -> str:
        type = ""
        match self:
            case self.SKIP:
                return "SKIP"
            case self.REVERSE:
                return "REVERSE"
            case self.DRAW_TWO:
                return "DRAW TWO"
            case self.WILD_DRAW_FOUR:
                return "DRAW FOUR"
        return type


@dataclasses.dataclass(order=True)
class Card:
    color: Color
    type: Type
    number: int | None = None

    def __str__(self) -> str:
        if self.type == Type.NUMBER:
            return f"{self.color} {self.number}"
        elif self.type == Type.WILD:
            return f"{self.color}"
        else:
            return f"{self.color} {self.type}"

    def playable(self, last: Card) -> bool:
        return (
            self.type in {Type.WILD, Type.WILD_DRAW_FOUR}
            or self.type == last.type != Type.NUMBER
            or self.color == last.color
            or self.number == last.number is not None
        )


@dataclasses.dataclass
class Game:
    num: int = 0
    current: int = 0
    direction: int = 1
    deck: list[Card] = dataclasses.field(default_factory=list)
    hands: list[list[Card]] = dataclasses.field(default_factory=list)
    stack: list[Card] = dataclasses.field(default_factory=list)
    skip: bool = False
    draw: int = 0

    def __post_init__(self) -> None:
        while self.num < 2:
            try:
                self.num = int(input("Welcome to Oh No! How many people will be playing? "))
            except ValueError:
                pass

        for color in [Color.RED, Color.YELLOW, Color.GREEN, Color.BLUE]:
            self.deck.append(Card(color, Type.NUMBER, 0))
            for number in range(1, 10):
                self.deck.extend([Card(color, Type.NUMBER, number)] * 2)
            self.deck.extend([Card(color, Type.SKIP)] * 2)
            self.deck.extend([Card(color, Type.REVERSE)] * 2)
            self.deck.extend([Card(color, Type.DRAW_TWO)] * 2)
        self.deck.extend([Card(Color.WILD, Type.WILD)] * 4)
        self.deck.extend([Card(Color.WILD, Type.WILD_DRAW_FOUR)] * 4)
        random.shuffle(self.deck)

        for hand in range(self.num):
            self.hands.append(self.deck[-7:])
            del self.deck[-7:]
            self.hands[hand].sort()

    def play(self) -> None:
        print("\n~~~ PLAYER 1's TURN ~~~")
        self.print_hand()
        self.choose_card()
        self.card_action()

        while len(self.hands[self.current]) != 0:
            self.turn()

        print(f"\nPlayer {self.current + 1} wins!")

    def print_hand(self, playable: list[int] | None = None) -> None:
        print("Here are the cards in your hand:")
        for i, card in enumerate(self.hands[self.current]):
            print(f"{i + 1}: {card}")
        if playable:
            print(f"""The last played card on the stack is a {self.stack[-1]}. You may play one of \
the following cards from your hand:""")
            for i, card in enumerate(playable):
                if i < len(playable) - 1:
                    print(f"{card + 1}", end=", ")
                else:
                    print(f"{card + 1}")

    def choose_card(self, playable: list[int] | None = None) -> None:
        while True:
            try:
                choice = int(input("Which card would you like to play? ")) - 1
                if not playable or choice in playable:
                    self.play_card(self.current, choice)
                    break
            except ValueError, IndexError:
                pass

    def play_card(self, hand: int, choice: int) -> None:
        self.stack.append(self.hands[hand][choice])
        print(f"You play a {self.hands[hand][choice]}")
        del self.hands[hand][choice]

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
                    continue

    def turn(self) -> None:
        self.rotate()
        print(f"\n~~~ PLAYER {self.current + 1}'s TURN ~~~")

        for _ in range(self.draw):
            self.draw_card()
        self.draw = 0

        if self.skip:
            print("Turn skipped")
            self.skip = False
            return

        playable = self.playable_cards()
        card_played = False
        if len(playable) == 0:
            print("You have no cards to play")
            self.draw_card()
            playable = self.playable_cards()
            if (playable) == 1:
                self.print_hand(playable)
                self.choose_card(playable)
                card_played = True
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
        print(f"You draw a {card} from the deck")
        self.hands[self.current].append(card)
        self.hands[self.current].sort()

    def playable_cards(self) -> list[int]:
        playable = []
        for i, card in enumerate(self.hands[self.current]):
            if card.playable(self.stack[-1]):
                playable.append(i)
        return playable


def main() -> None:
    game = Game()
    game.play()


if __name__ == "__main__":
    main()
