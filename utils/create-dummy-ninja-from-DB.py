#!/usr/bin/env python

"""
This script can be used to create "dummy" .ninja files, which replicate the
dependency structure of a build but eliminate all of the other details). This is
useful for constructing self contained .ninja files for use in performance
tests.
"""

import argparse

import sqlalchemy
import sqlalchemy.ext.declarative
from sqlalchemy import *

# DB Declaration

Base = sqlalchemy.ext.declarative.declarative_base()

class RuleResult(Base):
    __tablename__ = "rule_results"

    id = Column(Integer, nullable=False, primary_key=True)
    key = Column(String, nullable=False)
    value = Column(Integer, nullable=False)
    built_at = Column(Integer, nullable=False)
    computed_at = Column(Integer, nullable=False)

    dependencies = sqlalchemy.orm.relationship('RuleDependency')

    def __repr__(self):
        return "{0!s}{1!r}".format(
            self.__class__.__name__, (self.id, self.key, self.value,
                                      self.built_at, self.computed_at))

class RuleDependency(Base):
    __tablename__ = "rule_dependencies"

    id = Column(Integer, nullable=False, primary_key=True)
    rule_id = Column(Integer, ForeignKey(RuleResult.id),
                     nullable=False)
    key = Column(String, nullable=False)

    def __repr__(self):
        return "{0!s}{1!r}".format(
            self.__class__.__name__, (self.id, self.rule_id, self.key))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('path', metavar='path', type=str,
                        help='path to the database')
    parser.add_argument('--show-mapping', action='store_true',
                        help='show name to node-name mapping')
    args = parser.parse_args()

    # Create the database engine.
    engine = sqlalchemy.create_engine("sqlite:///" + args.path)

    # Create a session.
    session = sqlalchemy.orm.sessionmaker(engine)()

    # We create a dummy build file with one target "make-inputs", which creates
    # dummy input files, and all the other rules just cat those files together.
    print "rule CAT"
    print "    command = cat ${in} > ${out}"
    print "    description = ${command}"
    print
    node_names = {}
    def get_key_name(key):
        name = node_names.get(key)
        if name is None:
            node_names[key] = name = 'N{0:d}'.format(
                len(node_names) - len(input_rules))
        return name

    # First, find all the "inputs" (leaf nodes).
    input_rules = [rule
                   for rule in session.query(RuleResult)
                   if not rule.dependencies]

    # Assign all of the inputs special names.
    node_names.update((rule.key, "I{0:d}".format(i))
                      for i,rule in enumerate(input_rules))

    seen_rules = set()
    seen_inputs = set()
    seen_nodes = set()
    for rule in session.query(RuleResult):
        name = get_key_name(rule.key)
        dep_names = [get_key_name(dep.key)
                     for dep in rule.dependencies]
        if not dep_names:
            seen_inputs.add(name)
        else:
            print "build {0!s}: CAT {1!s}".format(name, " ".join(dep_names))
        seen_rules.add(name)
        seen_nodes.update(dep_names)
    print

    # Write a build statement to create all the inputs, so we can actually
    # execute the build.
    print "rule make-inputs"
    print "  command = touch {0!s}".format(" ".join(sorted(seen_inputs)))
    print "build make-inputs: make-inputs"
    print

    # Write out a default target with the roots.
    roots = seen_rules - seen_nodes
    print "default {0!s}".format(" ".join(roots))

    # Write the mappings, if requested.
    if args.show_mapping:
        print
        for key,name in sorted(node_names.items()):
            print "# {0!s} -> {1!s}".format(key, name)

if __name__ == '__main__':
    main()
