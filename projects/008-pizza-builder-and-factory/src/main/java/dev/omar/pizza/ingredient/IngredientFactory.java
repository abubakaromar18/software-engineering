package dev.omar.pizza.ingredient;

import dev.omar.pizza.domain.Ingredients.BakeProfile;
import dev.omar.pizza.domain.Ingredients.Cheese;
import dev.omar.pizza.domain.Ingredients.Dough;
import dev.omar.pizza.domain.Ingredients.Sauce;
import dev.omar.pizza.domain.Ingredients.Style;

/**
 * <b>Abstract Factory.</b> Creates a whole family of related products (dough, sauce, cheese and
 * the bake profile that suits them) without the caller naming any concrete product.
 *
 * <p>A store holds exactly one factory, so everything it puts on a pizza is guaranteed to come
 * from the same regional family: a Chicago store cannot accidentally use Neapolitan dough.
 */
public interface IngredientFactory {

    /** The family this factory produces. Every product it creates carries this style. */
    Style style();

    Dough createDough();

    Sauce createSauce();

    Cheese createCheese();

    BakeProfile bakeProfile();
}
