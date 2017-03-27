#!/usr/bin/env python

""" MultiQC module to parse output from Adapter Removal """

from __future__ import print_function
from collections import OrderedDict
import logging

from multiqc import config
from multiqc.plots import bargraph
from multiqc.plots import linegraph
from multiqc.modules.base_module import BaseMultiqcModule

# Initialise the logger
log = logging.getLogger(__name__)

class MultiqcModule(BaseMultiqcModule):

    def __init__(self):

        # Initialise the parent object
        super(MultiqcModule, self).__init__(name='Adapter Removal',
        anchor='adapterRemoval', target='Adapter Removal',
        href='https://github.com/MikkelSchubert/adapterremoval',
        info=" rapid adapter trimming, identification, and read merging ")

        self.__read_type = None
        self.__collapsed = None
        self.s_name = None
        self.adapter_removal_data = dict()
        self.arc_mate1 = dict()
        self.arc_mate2 = dict()
        self.arc_singleton = dict()
        self.arc_collapsed = dict()
        self.arc_collapsed_truncated = dict()
        self.arc_discarged = dict()
        self.arc_all = dict()

        for f in self.find_log_files(config.sp['adapterRemoval'], filehandles=True):
            self.s_name = f['s_name']
            try:
                parsed_data = self.parse_settings_file(f)
            except UserWarning:
                continue
            if parsed_data is not None:
                self.adapter_removal_data[self.s_name] = parsed_data

        if len(self.adapter_removal_data) == 0:
            log.debug("Could not find any reports in {}".format(config.analysis_dir))
            raise UserWarning

        log.info("Found {} reports".format(len(self.adapter_removal_data)))

        # todo:
        # Write parsed report data to a file

        self.intro += self.adapter_removal_counts_chart()
        self.intro += self.adapter_removal_length_dist_plot()

    def parse_settings_file(self, f):

        self.result_data = {
            'total': None,
            'unaligned': None,
            'aligned': None,
            'percent_aligned': None,
        }

        settings_data = {'header': []}

        block_title = None
        for i, line in enumerate(f['f']):

            line = line.rstrip('\n')
            if line == '':
                continue

            if not block_title:
                block_title = 'header'
                settings_data[block_title].append(str(line))
                continue

            if line.startswith('['):
                block_title = str(line.strip('[]'))
                settings_data[block_title] = []
                continue

            settings_data[block_title].append(str(line))

        # set data for further working
        self.set_result_data(settings_data)

        # todo: return or set by member var?
        return self.result_data

    def set_result_data(self, settings_data):
        self.set_trim_stat(settings_data['Trimming statistics'])
        self.set_len_dist(settings_data['Length distribution'])

    def set_trim_stat(self, trim_data):
        data_pattern = {'total': 0, 'unaligned': 1, 'aligned': 2}

        for title, key in data_pattern.iteritems():
            tmp = trim_data[key]
            value = tmp.split(': ')[1]
            self.result_data[title] = int(value)

        self.result_data['percent_aligned'] = round((self.result_data['aligned'] * 100) / self.result_data['total'], 2)

    def set_len_dist(self, len_dist_data):
        self.arc_mate1[self.s_name] = dict()
        self.arc_mate2[self.s_name] = dict()
        self.arc_singleton[self.s_name] = dict()
        self.arc_collapsed[self.s_name] = dict()
        self.arc_collapsed_truncated[self.s_name] = dict()
        self.arc_discarged[self.s_name] = dict()
        self.arc_all[self.s_name] = dict()

        head_line = len_dist_data[0].rstrip('\n').split('\t')
        self.__read_type = 'paired' if head_line[2] == 'Mate2' else 'single'
        self.__collapsed = True if head_line[-3] == 'CollapsedTruncated' else False

        for line in len_dist_data[1:]:
            l_data = line.rstrip('\n').split('\t')
            l_data = map(int, l_data)
            if self.__read_type == 'single':
                if not self.__collapsed:
                    self.arc_mate1[self.s_name][l_data[0]] = l_data[1]
                    self.arc_discarged[self.s_name][l_data[0]] = l_data[2]
                    self.arc_all[self.s_name][l_data[0]] = l_data[3]
                else:
                    # biological/technical relevance is not clear
                    log.warning("Case single-end and collapse is not "\
                                "implemented -> File %s skipped" % self.s_name)
                    raise UserWarning
            else:
                if not self.__collapsed:
                    self.arc_mate1[self.s_name][l_data[0]] = l_data[1]
                    self.arc_mate2[self.s_name][l_data[0]] = l_data[2]
                    self.arc_singleton[self.s_name][l_data[0]] = l_data[3]
                    self.arc_discarged[self.s_name][l_data[0]] = l_data[4]
                    self.arc_all[self.s_name][l_data[0]] = l_data[5]
                else:
                    self.arc_mate1[self.s_name][l_data[0]] = l_data[1]
                    self.arc_mate2[self.s_name][l_data[0]] = l_data[2]
                    self.arc_singleton[self.s_name][l_data[0]] = l_data[3]
                    self.arc_collapsed[self.s_name][l_data[0]] = l_data[4]
                    self.arc_collapsed_truncated[self.s_name][l_data[0]] = l_data[5]
                    self.arc_discarged[self.s_name][l_data[0]] = l_data[6]
                    self.arc_all[self.s_name][l_data[0]] = l_data[7]

    def adapter_removal_counts_chart(self):

        cats = OrderedDict()
        cats['aligned'] = {'name': 'aligned'}
        cats['unaligned'] = {'name': 'unaligned'}
        config = {
            'id': 'adapter_removal_alignment_plot',
            'title': 'Adapter Removal Alignments',
            'ylab': '# Reads',
            'hide_zero_cats': False,
            'cpswitch_counts_label': 'Number of Reads'
        }
        return bargraph.plot(self.adapter_removal_data, cats, config)

    def adapter_removal_length_dist_plot(self):

        html = '<p>add description here...</p>'

        pconfig = {
            'id': 'adapter_removal_lenght_count_plot',
            'title': 'Lengths of Trimmed Sequences',
            'ylab': 'Counts',
            'xlab': 'Length Trimmed (bp)',
            'xDecimals': False,
            'ymin': 0,
            'tt_label': '<b>{point.x} bp trimmed</b>: {point.y:.0f}',
            'data_labels': []
        }

        dl_mate1 = {'name': 'Mate1', 'ylab': 'Count'}
        dl_mate2 = {'name': 'Mate2', 'ylab': 'Count'}
        dl_singleton = {'name': 'Singleton', 'ylab': 'Count'}
        dl_collapsed = {'name': 'Collapsed', 'ylab': 'Count'}
        dl_collapsed_truncated = {'name': 'Collapsed Truncated', 'ylab': 'Count'}
        dl_discarded = {'name': 'Discarded', 'ylab': 'Count'}
        dl_all = {'name': 'All', 'ylab': 'Count'}

        if self.__read_type == 'single':
            if not self.__collapsed:
                lineplot_data = [self.arc_mate1, self.arc_discarged, self.arc_all]
                pconfig['data_labels'].extend([dl_mate1, dl_discarded, dl_all])
            else:
                # this case should not be reached (see case at method set_len_dist())
                pass
        else:
            if not self.__collapsed:
                lineplot_data = [self.arc_mate1, self.arc_mate2, self.arc_singleton, self.arc_discarged, self.arc_all]
                pconfig['data_labels'].extend([dl_mate1, dl_mate2, dl_singleton, dl_discarded, dl_all])
            else:
                lineplot_data = [self.arc_mate1, self.arc_mate2, self.arc_singleton, self.arc_collapsed, self.arc_collapsed_truncated, self.arc_discarged, self.arc_all]
                pconfig['data_labels'].extend([dl_mate1, dl_mate2, dl_singleton, dl_collapsed, dl_collapsed_truncated, dl_discarded, dl_all])

        html += linegraph.plot(lineplot_data, pconfig)
        return html