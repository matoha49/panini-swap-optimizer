import pandas as pd
import streamlit as st

from optimizer import (
    evaluate_album_change,
    find_stickers_to_give,
    find_stickers_to_give_even_if_last_copy,
    load_collection,
    recommend_equal_swap,
    recommend_maximum_martin_gain_swap,
    recommend_maximum_matej_gain_swap,
    recommend_maximum_total_swap,
)


RULES = (
    "Kus za kus",
    "Najväčší spoločný zisk",
    "Najväčší zisk pre prvého zberateľa",
    "Najväčší zisk pre druhého zberateľa",
)


def load_uploaded_collection(uploaded_file, collector_name):
    """Načíta nahrané CSV a doplní kontroly potrebné pre webové rozhranie."""
    try:
        uploaded_file.seek(0)
        collection = load_collection(uploaded_file)
    except Exception as error:
        raise ValueError(
            f"CSV pre zberateľa {collector_name} sa nepodarilo načítať: {error}"
        ) from error

    if collection["sticker_id"].isna().any():
        raise ValueError(
            f"CSV pre zberateľa {collector_name} obsahuje prázdne sticker_id."
        )

    if collection["sticker_id"].duplicated().any():
        raise ValueError(
            f"CSV pre zberateľa {collector_name} obsahuje duplicitné sticker_id."
        )

    numeric_counts = pd.to_numeric(collection["count"], errors="coerce")
    if numeric_counts.isna().any():
        raise ValueError(
            f"CSV pre zberateľa {collector_name} obsahuje neplatnú hodnotu count."
        )
    if (numeric_counts % 1 != 0).any():
        raise ValueError(
            f"CSV pre zberateľa {collector_name} musí mať v count celé čísla."
        )

    collection = collection.copy()
    collection["count"] = numeric_counts.astype(int)
    return collection


def calculate_trade(first_collection, second_collection, selected_rule):
    """Použije existujúce optimalizačné funkcie podľa zvoleného pravidla."""
    first_duplicates = find_stickers_to_give(
        first_collection,
        second_collection,
    )
    second_duplicates = find_stickers_to_give(
        second_collection,
        first_collection,
    )

    if selected_rule == RULES[0]:
        return recommend_equal_swap(first_duplicates, second_duplicates)

    if selected_rule == RULES[1]:
        return recommend_maximum_total_swap(
            first_duplicates,
            second_duplicates,
        )

    if selected_rule == RULES[2]:
        second_all_available = find_stickers_to_give_even_if_last_copy(
            second_collection,
            first_collection,
        )
        return recommend_maximum_matej_gain_swap(
            first_duplicates,
            second_all_available,
        )

    first_all_available = find_stickers_to_give_even_if_last_copy(
        first_collection,
        second_collection,
    )
    return recommend_maximum_martin_gain_swap(
        first_all_available,
        second_duplicates,
    )


def sticker_table(sticker_ids):
    """Vytvorí tabuľku vhodnú na zobrazenie zoznamu nálepiek."""
    return pd.DataFrame({"Nálepka": sticker_ids})


def show_collector_result(name, result, show_last_copies):
    """Zobrazí súhrn zmeny albumu jedného zberateľa."""
    st.subheader(name)
    metrics = st.columns(5)
    metrics[0].metric("Nové nálepky", len(result["new_stickers"]))
    metrics[1].metric(
        "Stratené posledné kusy",
        len(result["lost_last_copies"]),
    )
    metrics[2].metric("Čistá zmena", f"{result['net_change']:+d}")
    metrics[3].metric("Album pred výmenou", result["album_before"])
    metrics[4].metric("Album po výmene", result["album_after"])

    if show_last_copies:
        st.markdown("**Odovzdané posledné kusy**")
        if result["lost_last_copies"]:
            st.dataframe(
                sticker_table(result["lost_last_copies"]),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("Tento zberateľ neodovzdáva žiadny posledný kus.")


def main():
    st.set_page_config(
        page_title="Panini Swap Optimizer",
        page_icon="⚽",
        layout="wide",
    )
    st.title("⚽ Panini Swap Optimizer")
    st.write("Nahrajte dve zbierky a vyberte pravidlo výmeny.")

    name_columns = st.columns(2)
    first_name = name_columns[0].text_input("Meno prvého zberateľa", "Matej")
    second_name = name_columns[1].text_input("Meno druhého zberateľa", "Martin")

    file_columns = st.columns(2)
    first_file = file_columns[0].file_uploader(
        f"CSV súbor – {first_name or 'prvý zberateľ'}",
        type="csv",
        key="first_file",
    )
    second_file = file_columns[1].file_uploader(
        f"CSV súbor – {second_name or 'druhý zberateľ'}",
        type="csv",
        key="second_file",
    )

    selected_rule = st.selectbox("Pravidlo výmeny", RULES)
    if selected_rule == RULES[2]:
        st.warning(
            f"Pri tomto pravidle môže {second_name or 'druhý zberateľ'} "
            "odovzdať aj svoj posledný kus nálepky."
        )
    elif selected_rule == RULES[3]:
        st.warning(
            f"Pri tomto pravidle môže {first_name or 'prvý zberateľ'} "
            "odovzdať aj svoj posledný kus nálepky."
        )

    if not st.button("Vypočítať výmenu", type="primary"):
        return

    if not first_name.strip() or not second_name.strip():
        st.error("Zadajte meno oboch zberateľov.")
        return
    if first_file is None or second_file is None:
        st.error("Nahrajte oba CSV súbory.")
        return

    try:
        first_collection = load_uploaded_collection(first_file, first_name)
        second_collection = load_uploaded_collection(second_file, second_name)
        first_trade, second_trade = calculate_trade(
            first_collection,
            second_collection,
            selected_rule,
        )
        first_result = evaluate_album_change(
            first_collection,
            first_trade,
            second_trade,
        )
        second_result = evaluate_album_change(
            second_collection,
            second_trade,
            first_trade,
        )
    except Exception as error:
        st.error(f"Výmenu sa nepodarilo vypočítať: {error}")
        return

    st.divider()
    st.header("Odporúčaná výmena")
    trade_columns = st.columns(2)
    with trade_columns[0]:
        st.subheader(f"{first_name} dáva")
        st.dataframe(
            sticker_table(first_trade),
            hide_index=True,
            use_container_width=True,
        )
    with trade_columns[1]:
        st.subheader(f"{second_name} dáva")
        st.dataframe(
            sticker_table(second_trade),
            hide_index=True,
            use_container_width=True,
        )

    show_last_copies = selected_rule in RULES[2:]
    st.header("Vplyv na albumy")
    show_collector_result(first_name, first_result, show_last_copies)
    show_collector_result(second_name, second_result, show_last_copies)


if __name__ == "__main__":
    main()
