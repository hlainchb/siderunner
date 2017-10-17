"""

    Program.....: sidetest.py
    Author......: Herb Lainchbury
    License.....: (C) 2012 Dynamic Solutions Inc.
    Description.: SeleniumIDE test runner for Python

    Runs tests built in Selenium IDE using WebDriver in place without the need
    to export those tests.

    TODO:
      * subclass tests from unittest.TestCase?

"""
# pylint: disable=C0111, C0103, R0201

import os
import xml.dom.minidom
import logging
import unittest

from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException

__all__ = ['SeleniumTestCase', 'SeleniumTestSuite', 'SeleniumTests']

logger = logging.getLogger(__name__)
selenium_logger = logging.getLogger('selenium')
selenium_logger.setLevel(logging.INFO)
easyprocess_logger = logging.getLogger('easyprocess')
easyprocess_logger.setLevel(logging.INFO)

target_cache = {}


def to_text(node):
    """return node text"""
    if hasattr(node, 'data'):
        return node.data
    elif node.toxml() == '<br/>':
        return '\n'
    else:
        return ''


def get_command(nodes):
    """get node text"""
    result = []
    for node in nodes:
        if node.childNodes == []:
            result.append(None)
        else:
            result.append(''.join(to_text(n) for n in node.childNodes))
    return result


def find_element(driver, target):
    """find an element in the page"""

    if target in target_cache:
        target = target_cache[target]

    if target.startswith('link='):
        try:
            return driver.find_element_by_link_text(target[5:])
        except NoSuchElementException:
            # try lowercase version of link, work around text-transform bug
            result = driver.find_element_by_link_text(target[5:].lower())
            target_cache[target] = 'link=' + target[5:].lower()
            msg = '   label %s is being cached as %s'
            logger.info(msg, target, target_cache[target])
            return result

    elif target.startswith('//'):
        return driver.find_element_by_xpath(target)

    elif target.startswith('xpath='):
        return driver.find_element_by_xpath(target[6:])

    elif target.startswith('css='):
        return driver.find_element_by_css_selector(target[4:])

    elif target.startswith('id='):
        return driver.find_element_by_id(target[3:])

    elif target.startswith('name='):
        return driver.find_element_by_name(target[5:])

    else:
        direct = (
            driver.find_element_by_name(target) or
            driver.find_element_by_id(target) or
            driver.find_element_by_link_text(target)
        )
        if direct:
            return direct
        raise Exception('Don\'t know how to find %s' % target)


class SeleniumTestCase(object):
    """A Single Selenium Test Case"""

    def __init__(self, filename, callback=None):
        self.filename = filename
        self.callback = callback
        self.base_url = None
        self.commands = []

        document = open(filename).read()
        dom = xml.dom.minidom.parseString(document)

        rows = dom.getElementsByTagName('tr')
        for row in rows[1:]:
            self.commands.append(get_command(row.getElementsByTagName('td')))

        for command in self.commands:
            if not hasattr(self, str(command[0])):
                raise Exception('Unknown Selenium IDE command %s' % command)

    def run(self, driver, url):

        self.base_url = url

        logger.info('running '+self.filename)

        for command in self.commands:
            method = getattr(self, str(command[0]))
            args = []
            if command[1] is not None:
                args.append(command[1])
            if command[2] is not None:
                args.append(command[2])
            logger.info(
                '   ' + ' '.join(
                    [command[0]]+[repr(a) for a in args]
                ).splitlines()[0]
            )
            method(driver, *args)
            if self.callback:
                self.callback(driver.page_source)

    def open(self, driver, url):
        driver.get(self.base_url + url)

    def click(self, driver, target):
        element = find_element(driver, target)
        driver.execute_script("arguments[0].scrollIntoView();", element)
        element.click()

    def clickAndWait(self, driver, target):
        self.click(driver, target)

    def type(self, driver, target, text=''):
        element = find_element(driver, target)
        element.click()
        element.clear()
        element.send_keys(text)

    def select(self, driver, target, value):
        element = find_element(driver, target)
        if value.startswith('label='):
            Select(element).select_by_visible_text(value[6:])
        else:
            msg = "Don\'t know how to select %s on %s"
            raise Exception(msg % (value, target))

    def verifyTextPresent(self, driver, text):
        try:
            source = driver.page_source
            assert bool(text in source)
        except:
            print(
                'verifyTextPresent: ',
                repr(text),
                'not present in',
                repr(source)
            )
            raise

    def verifyTextNotPresent(self, driver, text):
        try:
            assert not bool(text in driver.page_source)
        except:
            print(
                'verifyNotTextPresent: ',
                repr(text),
                'present'
            )
            raise

    def assertElementPresent(self, driver, target):
        try:
            assert bool(find_element(driver, target))
        except:
            print('assertElementPresent: ', repr(target), 'not present')
            raise

    def verifyElementPresent(self, driver, target):
        try:
            assert bool(find_element(driver, target))
        except:
            print('verifyElementPresent: ', repr(target), 'not present')
            raise

    def verifyElementNotPresent(self, driver, target):
        present = True
        try:
            find_element(driver, target)
        except NoSuchElementException:
            present = False

        try:
            assert not present
        except:
            print('verifyElementNotPresent: ', repr(target), 'present')
            raise

    def waitForTextPresent(self, driver, text):
        try:
            assert bool(text in driver.page_source)
        except:
            print('waitForTextPresent: ', repr(text), 'not present')
            raise

    def waitForTextNotPresent(self, driver, text):
        try:
            assert not bool(text in driver.page_source)
        except:
            print('waitForTextNotPresent: ', repr(text), 'present')
            raise

    def assertText(self, driver, target, value=u''):
        try:
            target_value = find_element(driver, target).text
            logger.info('   assertText target value =' + repr(target_value))
            if value.startswith('exact:'):
                assert target_value == value[len('exact:'):]
            else:
                assert target_value == value
        except:
            print(
                'assertText: ',
                repr(target),
                repr(find_element(driver, target).get_attribute('value')),
                repr(value),
            )
            raise

    def assertNotText(self, driver, target, value=u''):
        try:
            target_value = find_element(driver, target).text
            logger.info('  assertNotText target value =' + repr(target_value))
            if value.startswith('exact:'):
                assert target_value != value[len('exact:'):]
            else:
                assert target_value != value
        except:
            print(
                'assertNotText: ',
                repr(target),
                repr(find_element(driver, target).get_attribute('value')),
                repr(value),
            )
            raise

    def assertValue(self, driver, target, value=u''):
        try:
            target_value = find_element(driver, target).get_attribute('value')
            logger.info('  assertValue target value ='+repr(target_value))
            assert target_value == value
        except:
            print(
                'assertValue: ',
                repr(target),
                repr(find_element(driver, target).get_attribute('value')),
                repr(value),
            )
            raise

    def assertNotValue(self, driver, target, value=u''):
        try:
            target_value = find_element(driver, target).get_attribute('value')
            logger.info('  assertNotValue target value ='+repr(target_value))
            assert target_value != value
        except:
            print(
                'assertNotValue: ',
                repr(target),
                repr(target_value),
                repr(value),
            )
            raise

    def verifyValue(self, driver, target, value=u''):
        try:
            target_value = find_element(driver, target).get_attribute('value')
            logger.info('  verifyValue target value ='+repr(target_value))
            assert target_value == value
        except:
            print(
                'verifyValue: ',
                repr(target),
                repr(find_element(driver, target).get_attribute('value')),
                repr(value),
            )
            raise

    def selectWindow(self, driver, window):
        pass


class SeleniumTestSuite(object):
    """A Selenium Test Suite"""

    def __init__(self, filename, callback=None):

        def get_test_rows(dom):
            return dom.getElementsByTagName('tr')

        def get_suite_title(row):
            return row.getElementsByTagName('b')[0].childNodes[0].data

        def get_test_title(row):
            return row.getElementsByTagName('a')[0].childNodes[0].data

        def get_filename(row):
            return row.getElementsByTagName('a')[0].attributes.items()[0][1]

        path = os.path.abspath(os.path.split(filename)[0])
        self.callback = callback

        document = open(filename).read()
        dom = xml.dom.minidom.parseString(document)

        self.tests = []

        rows = get_test_rows(dom)
        self.title = get_suite_title(rows[0])

        for row in rows[1:]:
            title = get_test_title(row)
            test_filename = get_filename(row)

            pathname = os.path.join(path, test_filename)
            logger.debug('loading test: %s', pathname)
            test_case = SeleniumTestCase(pathname, self.callback)
            self.tests.append((title, test_case))

    def run(self, driver, url):
        for title, test in self.tests:
            try:
                test.run(driver, url)
            except:
                print('Error in %s (%s)' % (title, test.filename))
                raise

    def __repr__(self):
        tests = '\n'.join(['%s - %s' % (title, test.filename)
                           for title, test in self.tests])
        return '%s\n%s' % (self.title, tests)


class SeleniumTests(unittest.TestCase):
    """A Set of Selenium Test Suites"""

    url = 'http://localhost'
    headless = True
    size = (1024, 768)
    logger = logging.getLogger(__name__)
    path = '.'

    def get_driver(self):
        return webdriver.Chrome()

    def setUp(self):
        if self.headless:
            self.logger.info('running headless')
            self.display = Display(visible=0, size=self.size)
            self.display.start()
        else:
            self.logger.info('not running headless')

        self.driver = self.get_driver()
        self.driver.set_window_size(*self.size)
        self.driver.implicitly_wait(10)

    def tearDown(self):
        if self.headless:
            self.display.stop()

        self.driver.quit()

    def run_suite(self, suite_name):
        # logger = self.logger
        logger.debug('running test against %s', self.url)
        suite_file = os.path.join(self.path, suite_name)
        if os.path.isfile(suite_file):
            tests = SeleniumTestSuite(suite_file, self.check_for_errors)
            try:
                logger.debug('running suite %s', suite_file)
                tests.run(self.driver, self.url)
            except:
                self.driver.save_screenshot('%s-error_screen.png' % suite_name)
                raise
        else:
            raise Exception('suite %r missing' % suite_file)

    def check_for_errors(self, text):
        pass
