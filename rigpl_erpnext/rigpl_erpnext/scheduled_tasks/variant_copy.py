# -*- coding: utf-8 -*-
# Copyright (c) 2015, Rohit Industries Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from rigpl_erpnext.rigpl_erpnext.scheduled_tasks.item_valuation_rate import set_valuation_rate
import json
import sys

#Run this script every hour but to ensure that there is no server overload run it only for 1 template at a time

def check_wrong_variants():
	set_valuation_rate()
	update_templates()
	limit_set = int(frappe.db.get_single_value("Stock Settings", "automatic_sync_field_limit"))
	is_sync_allowed = frappe.db.get_single_value("Stock Settings", 
		"automatically_sync_templates_data_to_items")
	if is_sync_allowed == 1:
		templates = frappe.db.sql("""SELECT it.name, (SELECT count(name) 
			FROM `tabItem` WHERE variant_of = it.name) as variants 
			FROM `tabItem` it WHERE it.has_variants = 1 
			AND it.disabled = 0 AND it.end_of_life >= CURDATE()
			ORDER BY variants DESC""", as_list=1)
		sno = 0
		for t in templates:
			sno += 1
			print (str(sno) + " " + t[0] + " has variants = " + str(t[1]))
		fields_edited = 0
		for t in templates:
			print (str(t[0]) + " Has No of Variants = " + str(t[1]))
			if fields_edited <= limit_set:
				temp_doc = frappe.get_doc("Item", t[0])
				variants = frappe.db.sql("""SELECT name FROM `tabItem` WHERE variant_of = '%s'
					ORDER BY modified ASC"""%(t[0]), as_list=1)
				#Check all variants' fields are matching with template if 
				#not then copy the fields else go to next item
				for item in variants:
					print ("Checking Item = " + item[0])
					it_doc = frappe.get_doc("Item", item[0])
					fields_edited += check_and_copy_attributes_to_variant(temp_doc, it_doc)
			else:
				print ("Limit of " + str(limit_set) + " fields reached. Run again for more updating")
				break

def update_templates():
	variant_list = frappe.db.sql("""SELECT name FROM `tabItem` WHERE has_variants = 1""", as_list=1)
	for variants in variant_list:
		it_doc = frappe.get_doc("Item", variants[0])
		if it_doc.is_purchase_item == 1:
			if it_doc.default_material_request_type != 'Purchase':
				it_doc.default_material_request_type = 'Purchase'
				it_doc.save()
				print("Update Template : " + it_doc.name)
		else:
			if it_doc.default_material_request_type == 'Purchase':
				it_doc.default_material_request_type = 'Manufacture'
				it_doc.save()
				print("Update Template : " + it_doc.name)
		frappe.db.commit()
		
				
def check_and_copy_attributes_to_variant(template, variant):
	from frappe.model import no_value_fields
	check = 0
	save_chk = 0
	copy_field_list = frappe.db.sql("""SELECT field_name FROM `tabVariant Field`""", as_list=1)
	include_fields = []
	for fields in copy_field_list:
		include_fields.append(fields[0])

	for field in template.meta.fields:
		# "Table" is part of `no_value_field` but we shouldn't ignore tables
		if (field.fieldtype == 'Table' or field.fieldtype not in no_value_fields) \
			and (not field.no_copy) and field.fieldname in include_fields:
			if variant.get(field.fieldname) != template.get(field.fieldname):
				variant.set(field.fieldname, template.get(field.fieldname))
				save_chk = 1
				print ("Updated Item " + variant.name + " Field Changed = " + str(field.label) + 
					" Updated Value to " + str(template.get(field.fieldname)))
				check += 1
	if save_chk == 1:
		variant.save()
		frappe.db.commit()
		print ("Item Code " + variant.name + " Saved")
	return check
