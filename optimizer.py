import pandas as pd


def load_collection(filename):
    """Načíta zbierku zo súboru CSV."""
    collection = pd.read_csv(filename)

    required_columns = {"sticker_id", "count"}

    if not required_columns.issubset(collection.columns):
        raise ValueError(
            f"Súbor {filename} musí obsahovať stĺpce sticker_id a count."
        )

    if (collection["count"] < 0).any():
        raise ValueError(
            f"Súbor {filename} obsahuje záporný počet nálepiek."
        )

    return collection


def find_stickers_to_give(owner, recipient):
    """
    Nájde nálepky, ktoré má vlastník aspoň dvakrát
    a príjemca ich ešte nemá.
    """
    merged = owner.merge(
        recipient,
        on="sticker_id",
        suffixes=("_owner", "_recipient"),
    )

    possible_stickers = merged[
        (merged["count_owner"] >= 2)
        & (merged["count_recipient"] == 0)
    ]

    return sorted(possible_stickers["sticker_id"].tolist())


def find_stickers_to_give_even_if_last_copy(owner, recipient):
    """
    Nájde všetky nálepky, ktoré vlastník má aspoň raz
    a príjemca ich ešte nemá.
    """
    merged = owner.merge(
        recipient,
        on="sticker_id",
        suffixes=("_owner", "_recipient"),
    )

    possible_stickers = merged[
        (merged["count_owner"] >= 1)
        & (merged["count_recipient"] == 0)
    ]

    return sorted(possible_stickers["sticker_id"].tolist())


def recommend_equal_swap(matej_gives, martin_gives):
    """Obaja odovzdajú rovnaký počet nálepiek."""
    trade_size = min(len(matej_gives), len(martin_gives))

    return (
        matej_gives[:trade_size],
        martin_gives[:trade_size],
    )


def recommend_maximum_total_swap(matej_gives, martin_gives):
    """
    Použijú sa všetky užitočné nálepky.
    Počet nálepiek na oboch stranách nemusí byť rovnaký.
    """
    return matej_gives, martin_gives


def recommend_maximum_matej_gain_swap(matej_gives, martin_gives_for_matej):
    """Prioritne doplní Matejov album, aj z Martinových posledných kusov."""
    return matej_gives, martin_gives_for_matej


def recommend_maximum_martin_gain_swap(matej_gives_for_martin, martin_gives):
    """Prioritne doplní Martinov album, aj z Matejových posledných kusov."""
    return matej_gives_for_martin, martin_gives


def evaluate_album_change(collection, stickers_given, stickers_received):
    """Vypočíta vplyv výmeny na počet rôznych nálepiek v albume."""
    counts = collection.set_index("sticker_id")["count"]

    new_stickers = [
        sticker_id
        for sticker_id in stickers_received
        if counts.get(sticker_id, 0) == 0
    ]
    lost_last_copies = [
        sticker_id
        for sticker_id in stickers_given
        if counts.get(sticker_id, 0) == 1
    ]

    album_before = int((collection["count"] > 0).sum())
    net_change = len(new_stickers) - len(lost_last_copies)
    album_after = album_before + net_change

    return {
        "new_stickers": new_stickers,
        "lost_last_copies": lost_last_copies,
        "net_change": net_change,
        "album_before": album_before,
        "album_after": album_after,
    }


def print_person_result(name, result, show_last_copy_details):
    """Vypíše vyhodnotenie výmeny pre jedného používateľa."""
    print(f"\n{name}:")
    print(f"- dostane {len(result['new_stickers'])} nových nálepiek")
    print(
        "- stratí "
        f"{len(result['lost_last_copies'])} posledných kusov"
    )
    print(f"- čistá zmena albumu: {result['net_change']:+d}")
    print(f"- počet nálepiek v albume pred výmenou: {result['album_before']}")
    print(f"- počet nálepiek v albume po výmene: {result['album_after']}")

    if show_last_copy_details:
        print(
            "- nálepky odovzdané ako posledný kus: "
            f"{result['lost_last_copies']}"
        )


def print_trade(
    matej_trade,
    martin_trade,
    mode_name,
    matej_collection,
    martin_collection,
    show_last_copy_details=False,
):
    """Vypíše výsledok a vplyv odporúčanej výmeny na oba albumy."""
    print(f"\nODPORÚČANÁ VÝMENA – {mode_name}")

    print("\nMatej dá Martinovi:")
    print(matej_trade)

    print("\nMartin dá Matejovi:")
    print(martin_trade)

    matej_result = evaluate_album_change(
        matej_collection,
        matej_trade,
        martin_trade,
    )
    martin_result = evaluate_album_change(
        martin_collection,
        martin_trade,
        matej_trade,
    )

    print_person_result("Matej", matej_result, show_last_copy_details)
    print_person_result("Martin", martin_result, show_last_copy_details)

    matej_gain = len(matej_result["new_stickers"])
    martin_gain = len(martin_result["new_stickers"])
    total_gain = matej_gain + martin_gain
    difference = abs(matej_gain - martin_gain)

    print(f"\nSpoločný hrubý zisk je {total_gain} nových nálepiek.")
    print(f"Rozdiel medzi ziskom hráčov je {difference}.")


def main():
    """Spustí pôvodné terminálové používateľské rozhranie."""
    matej = load_collection("matej.csv")
    martin = load_collection("martin.csv")

    matej_gives = find_stickers_to_give(matej, martin)
    martin_gives = find_stickers_to_give(martin, matej)
    matej_gives_for_martin = find_stickers_to_give_even_if_last_copy(
        matej,
        martin,
    )
    martin_gives_for_matej = find_stickers_to_give_even_if_last_copy(
        martin,
        matej,
    )

    print("VYBER PRAVIDLO VÝMENY")
    print("1 – Kus za kus")
    print("2 – Najväčší spoločný zisk")
    print("3 – Najväčší zisk pre Mateja")
    print("4 – Najväčší zisk pre Martina")

    choice = input("\nNapíš 1, 2, 3 alebo 4 a stlač Enter: ")

    if choice == "1":
        matej_trade, martin_trade = recommend_equal_swap(
            matej_gives,
            martin_gives,
        )
        mode_name = "KUS ZA KUS"
        show_last_copy_details = False

    elif choice == "2":
        matej_trade, martin_trade = recommend_maximum_total_swap(
            matej_gives,
            martin_gives,
        )
        mode_name = "NAJVÄČŠÍ SPOLOČNÝ ZISK"
        show_last_copy_details = False

    elif choice == "3":
        matej_trade, martin_trade = recommend_maximum_matej_gain_swap(
            matej_gives,
            martin_gives_for_matej,
        )
        mode_name = "NAJVÄČŠÍ ZISK PRE MATEJA (PRAVIDLO 3)"
        show_last_copy_details = True

    elif choice == "4":
        matej_trade, martin_trade = recommend_maximum_martin_gain_swap(
            matej_gives_for_martin,
            martin_gives,
        )
        mode_name = "NAJVÄČŠÍ ZISK PRE MARTINA (PRAVIDLO 4)"
        show_last_copy_details = True

    else:
        print("\nNeplatná voľba. Spusti program znova a vyber 1, 2, 3 alebo 4.")
        return

    print_trade(
        matej_trade,
        martin_trade,
        mode_name,
        matej,
        martin,
        show_last_copy_details=show_last_copy_details,
    )


if __name__ == "__main__":
    main()
