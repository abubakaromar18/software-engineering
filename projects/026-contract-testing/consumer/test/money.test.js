import assert from 'node:assert/strict';
import { describe, test } from 'node:test';

import { Money } from '../src/money.js';

describe('Money', () => {
  test('formats minor units as currency', () => {
    assert.equal(new Money(4599, 'USD').format(), '$45.99');
    assert.equal(new Money(100, 'EUR').format('de-DE'), '1,00 €');
  });

  test('adds and multiplies without floating-point drift', () => {
    const total = new Money(10, 'USD').add(new Money(20, 'USD')).times(3);
    assert.equal(total.cents, 90);
  });

  test('rejects mixed currencies and non-integer amounts', () => {
    assert.throws(() => new Money(1, 'USD').add(new Money(1, 'EUR')), TypeError);
    assert.throws(() => new Money(1.5, 'USD'), TypeError);
    assert.throws(() => new Money(1, 'usd'), TypeError);
  });

  test('is immutable', () => {
    const money = new Money(1, 'USD');
    assert.throws(() => {
      money.cents = 2;
    }, TypeError);
  });
});
