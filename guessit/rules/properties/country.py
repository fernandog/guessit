#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
country property
"""
# pylint: disable=no-member
import babelfish

from rebulk import Rebulk
from ..common.words import COMMON_WORDS, iter_words


def country():
    """
    Builder for rebulk object.
    :return: Created Rebulk object
    :rtype: Rebulk
    """
    rebulk = Rebulk().defaults(name='country')

    rebulk.functional(find_countries,
                      #  Prefer language and any other property over country if not US or GB.
                      conflict_solver=lambda match, other: match
                      if other.name != 'language' or match.value not in (babelfish.Country('US'),
                                                                         babelfish.Country('GB'))
                      else other,
                      properties={'country': [None]})

    return rebulk


COUNTRIES_SYN = {'ES': ['españa'],
                 'GB': ['UK'],
                 'BR': ['brazilian', 'bra'],
                 'CA': ['québec', 'quebec', 'qc'],
                 # FIXME: this one is a bit of a stretch, not sure how to do it properly, though...
                 'MX': ['Latinoamérica', 'latin america']}


class GuessitCountryConverter(babelfish.CountryReverseConverter):  # pylint: disable=missing-docstring
    def __init__(self):
        self.guessit_exceptions = {}

        for alpha2, synlist in COUNTRIES_SYN.items():
            for syn in synlist:
                self.guessit_exceptions[syn.lower()] = alpha2

    @property
    def codes(self):  # pylint: disable=missing-docstring
        return (babelfish.country_converters['name'].codes |
                frozenset(babelfish.COUNTRIES.values()) |
                frozenset(self.guessit_exceptions.keys()))

    def convert(self, alpha2):
        if alpha2 == 'GB':
            return 'UK'
        return str(babelfish.Country(alpha2))

    def reverse(self, name):  # pylint:disable=arguments-differ
        # exceptions come first, as they need to override a potential match
        # with any of the other guessers
        try:
            return self.guessit_exceptions[name.lower()]
        except KeyError:
            pass

        try:
            return babelfish.Country(name.upper()).alpha2
        except ValueError:
            pass

        for conv in [babelfish.Country.fromname]:
            try:
                return conv(name).alpha2
            except babelfish.CountryReverseError:
                pass

        raise babelfish.CountryReverseError(name)


babelfish.country_converters['guessit'] = GuessitCountryConverter()


class CountryFinder(object):
    """Helper class to search and return country matches."""

    def __init__(self, allowed_countries):
        self.allowed_countries = set([l.lower() for l in allowed_countries or []])
        self.common_words = COMMON_WORDS

    def find(self, string):
        """Return all matches for country."""
        for word_match in iter_words(string.strip().lower()):
            word = word_match.value
            if word.lower() in self.common_words:
                continue

            try:
                country_object = babelfish.Country.fromguessit(word)
                if (not self.allowed_countries or
                        country_object.name.lower() in self.allowed_countries or
                        country_object.alpha2.lower() in self.allowed_countries):
                    yield self._to_rebulk_match(word_match, country_object)
            except babelfish.Error:
                continue

    @classmethod
    def _to_rebulk_match(cls, word, value):
        return word.span[0], word.span[1], {'value': value}


def find_countries(string, context=None):
    """
    Find countries in given string.
    """
    allowed_countries = context.get('allowed_countries') if context else None
    return CountryFinder(allowed_countries).find(string)
