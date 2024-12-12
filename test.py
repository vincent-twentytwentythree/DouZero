deckCards = [[], []]
with open("outputDeckCards.txt", "a") as file:
    file.write(", ".join(map(str, deckCards)) + "\n")