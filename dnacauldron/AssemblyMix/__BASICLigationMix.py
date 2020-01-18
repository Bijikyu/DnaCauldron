"""
"""

from Bio.Alphabet import DNAAlphabet


from ..biotools import annotate_record, set_record_topology
from ..Fragment.StickyEndFragment import (
    StickyEndFragment,
    StickyEndSeq,
    StickyEnd,
)
from ..Filter import NoRestrictionSiteFilter, TextSearchFilter
from .Type2sRestrictionMix import Type2sRestrictionMix


class BASICLigationMix(Type2sRestrictionMix):
    @staticmethod
    def find_adapter(record):
        for feature in record.features:
            label = feature.qualifiers.get("label", "")
            if isinstance(label, list):
                label = label[0]
            if label == "adapter":
                return (
                    int(feature.location.start),
                    int(feature.location.end),
                    feature.location.strand,
                )
        return None

    def fragments_filters(self):
        enzyme_filter = NoRestrictionSiteFilter(str(self.enzyme))
        return [lambda frag: (self.find_adapter(frag) or enzyme_filter(frag))]

    def compute_digest(self, construct):

        adapter = self.find_adapter(construct)
        if adapter:
            start, end, strand = adapter
            left_end = StickyEnd(str(construct[:start].seq), strand=1)
            right_end = StickyEnd(str(construct[end:].seq), strand=1)
            sequence = StickyEndSeq(
                str(construct[start:end].seq),
                left_end=left_end,
                right_end=right_end,
            )
            sequence.alphabet = DNAAlphabet()
            record = StickyEndFragment(seq=sequence)
            annotate_record(
                record, location=(0, len(sequence), 1), label="adapter"
            )
            return [record]
        else:
            # No feature shows that this is an adapter: use simple restriction
            return Type2sRestrictionMix.compute_digest(self, construct)

    @staticmethod
    def assemble_constructs_and_linkers(records_list, enzyme="BsaI"):
        fragments = []
        for linker_left, part, linker_right in records_list:
            set_record_topology(linker_left, topology="linear")
            set_record_topology(linker_right, topology="linear")
            if not isinstance(part, list):
                part = [part]

            for p in part:
                mix = BASICLigationMix(
                    [linker_left, p, linker_right], enzyme="BsaI"
                )
                mix.compute_linear_assemblies
                new_fragment = list(
                    mix.compute_linear_assemblies(
                        fragments_sets_filters=(),
                        min_parts=3,
                        seqrecord_filters=[TextSearchFilter("adapter")],
                        annotate_homologies=False,
                    )
                )
                if len(new_fragment) != 1:
                    part_names = str(
                        [linker_left.name, p.id, linker_right.name]
                    )
                    raise ValueError(
                        "Something weird happened when trying to assemble "
                        "%s. %d assemblies found"
                        % (part_names, len(new_fragment))
                    )
                new_fragment = new_fragment[0]
                new_fragment.original_part = p
                fragments.append(new_fragment)
        final_mix = BASICLigationMix(fragments=fragments)
        final_mix.compute_reverse_fragments()
        return final_mix.compute_circular_assemblies()