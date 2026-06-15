// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'app_database.dart';

// ignore_for_file: type=lint
class $ProductsTable extends Products
    with TableInfo<$ProductsTable, ProductLocal> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $ProductsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
      'id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _rowVersionMeta =
      const VerificationMeta('rowVersion');
  @override
  late final GeneratedColumn<int> rowVersion = GeneratedColumn<int>(
      'row_version', aliasedName, false,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultValue: const Constant(0));
  static const VerificationMeta _isDeletedMeta =
      const VerificationMeta('isDeleted');
  @override
  late final GeneratedColumn<bool> isDeleted = GeneratedColumn<bool>(
      'is_deleted', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_deleted" IN (0, 1))'),
      defaultValue: const Constant(false));
  static const VerificationMeta _lastModifiedHlcMeta =
      const VerificationMeta('lastModifiedHlc');
  @override
  late final GeneratedColumn<String> lastModifiedHlc = GeneratedColumn<String>(
      'last_modified_hlc', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _isSyncedMeta =
      const VerificationMeta('isSynced');
  @override
  late final GeneratedColumn<bool> isSynced = GeneratedColumn<bool>(
      'is_synced', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_synced" IN (0, 1))'),
      defaultValue: const Constant(true));
  static const VerificationMeta _brandIdMeta =
      const VerificationMeta('brandId');
  @override
  late final GeneratedColumn<String> brandId = GeneratedColumn<String>(
      'brand_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _categoryIdMeta =
      const VerificationMeta('categoryId');
  @override
  late final GeneratedColumn<String> categoryId = GeneratedColumn<String>(
      'category_id', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _nameMeta = const VerificationMeta('name');
  @override
  late final GeneratedColumn<String> name = GeneratedColumn<String>(
      'name', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _descriptionMeta =
      const VerificationMeta('description');
  @override
  late final GeneratedColumn<String> description = GeneratedColumn<String>(
      'description', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _basePriceMeta =
      const VerificationMeta('basePrice');
  @override
  late final GeneratedColumn<double> basePrice = GeneratedColumn<double>(
      'base_price', aliasedName, false,
      type: DriftSqlType.double, requiredDuringInsert: true);
  static const VerificationMeta _buyPriceMeta =
      const VerificationMeta('buyPrice');
  @override
  late final GeneratedColumn<double> buyPrice = GeneratedColumn<double>(
      'buy_price', aliasedName, true,
      type: DriftSqlType.double, requiredDuringInsert: false);
  static const VerificationMeta _skuMeta = const VerificationMeta('sku');
  @override
  late final GeneratedColumn<String> sku = GeneratedColumn<String>(
      'sku', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _barcodeMeta =
      const VerificationMeta('barcode');
  @override
  late final GeneratedColumn<String> barcode = GeneratedColumn<String>(
      'barcode', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _imageUrlMeta =
      const VerificationMeta('imageUrl');
  @override
  late final GeneratedColumn<String> imageUrl = GeneratedColumn<String>(
      'image_url', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _stockEnabledMeta =
      const VerificationMeta('stockEnabled');
  @override
  late final GeneratedColumn<bool> stockEnabled = GeneratedColumn<bool>(
      'stock_enabled', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints: GeneratedColumn.constraintIsAlways(
          'CHECK ("stock_enabled" IN (0, 1))'),
      defaultValue: const Constant(false));
  static const VerificationMeta _crdtPositiveMeta =
      const VerificationMeta('crdtPositive');
  @override
  late final GeneratedColumn<String> crdtPositive = GeneratedColumn<String>(
      'crdt_positive', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('{}'));
  static const VerificationMeta _crdtNegativeMeta =
      const VerificationMeta('crdtNegative');
  @override
  late final GeneratedColumn<String> crdtNegative = GeneratedColumn<String>(
      'crdt_negative', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('{}'));
  static const VerificationMeta _stockQtyMeta =
      const VerificationMeta('stockQty');
  @override
  late final GeneratedColumn<double> stockQty = GeneratedColumn<double>(
      'stock_qty', aliasedName, false,
      type: DriftSqlType.double,
      requiredDuringInsert: false,
      defaultValue: const Constant(0.0));
  static const VerificationMeta _isActiveMeta =
      const VerificationMeta('isActive');
  @override
  late final GeneratedColumn<bool> isActive = GeneratedColumn<bool>(
      'is_active', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_active" IN (0, 1))'),
      defaultValue: const Constant(true));
  @override
  List<GeneratedColumn> get $columns => [
        id,
        rowVersion,
        isDeleted,
        lastModifiedHlc,
        isSynced,
        brandId,
        categoryId,
        name,
        description,
        basePrice,
        buyPrice,
        sku,
        barcode,
        imageUrl,
        stockEnabled,
        crdtPositive,
        crdtNegative,
        stockQty,
        isActive
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'products';
  @override
  VerificationContext validateIntegrity(Insertable<ProductLocal> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('row_version')) {
      context.handle(
          _rowVersionMeta,
          rowVersion.isAcceptableOrUnknown(
              data['row_version']!, _rowVersionMeta));
    }
    if (data.containsKey('is_deleted')) {
      context.handle(_isDeletedMeta,
          isDeleted.isAcceptableOrUnknown(data['is_deleted']!, _isDeletedMeta));
    }
    if (data.containsKey('last_modified_hlc')) {
      context.handle(
          _lastModifiedHlcMeta,
          lastModifiedHlc.isAcceptableOrUnknown(
              data['last_modified_hlc']!, _lastModifiedHlcMeta));
    }
    if (data.containsKey('is_synced')) {
      context.handle(_isSyncedMeta,
          isSynced.isAcceptableOrUnknown(data['is_synced']!, _isSyncedMeta));
    }
    if (data.containsKey('brand_id')) {
      context.handle(_brandIdMeta,
          brandId.isAcceptableOrUnknown(data['brand_id']!, _brandIdMeta));
    } else if (isInserting) {
      context.missing(_brandIdMeta);
    }
    if (data.containsKey('category_id')) {
      context.handle(
          _categoryIdMeta,
          categoryId.isAcceptableOrUnknown(
              data['category_id']!, _categoryIdMeta));
    }
    if (data.containsKey('name')) {
      context.handle(
          _nameMeta, name.isAcceptableOrUnknown(data['name']!, _nameMeta));
    } else if (isInserting) {
      context.missing(_nameMeta);
    }
    if (data.containsKey('description')) {
      context.handle(
          _descriptionMeta,
          description.isAcceptableOrUnknown(
              data['description']!, _descriptionMeta));
    }
    if (data.containsKey('base_price')) {
      context.handle(_basePriceMeta,
          basePrice.isAcceptableOrUnknown(data['base_price']!, _basePriceMeta));
    } else if (isInserting) {
      context.missing(_basePriceMeta);
    }
    if (data.containsKey('buy_price')) {
      context.handle(_buyPriceMeta,
          buyPrice.isAcceptableOrUnknown(data['buy_price']!, _buyPriceMeta));
    }
    if (data.containsKey('sku')) {
      context.handle(
          _skuMeta, sku.isAcceptableOrUnknown(data['sku']!, _skuMeta));
    }
    if (data.containsKey('barcode')) {
      context.handle(_barcodeMeta,
          barcode.isAcceptableOrUnknown(data['barcode']!, _barcodeMeta));
    }
    if (data.containsKey('image_url')) {
      context.handle(_imageUrlMeta,
          imageUrl.isAcceptableOrUnknown(data['image_url']!, _imageUrlMeta));
    }
    if (data.containsKey('stock_enabled')) {
      context.handle(
          _stockEnabledMeta,
          stockEnabled.isAcceptableOrUnknown(
              data['stock_enabled']!, _stockEnabledMeta));
    }
    if (data.containsKey('crdt_positive')) {
      context.handle(
          _crdtPositiveMeta,
          crdtPositive.isAcceptableOrUnknown(
              data['crdt_positive']!, _crdtPositiveMeta));
    }
    if (data.containsKey('crdt_negative')) {
      context.handle(
          _crdtNegativeMeta,
          crdtNegative.isAcceptableOrUnknown(
              data['crdt_negative']!, _crdtNegativeMeta));
    }
    if (data.containsKey('stock_qty')) {
      context.handle(_stockQtyMeta,
          stockQty.isAcceptableOrUnknown(data['stock_qty']!, _stockQtyMeta));
    }
    if (data.containsKey('is_active')) {
      context.handle(_isActiveMeta,
          isActive.isAcceptableOrUnknown(data['is_active']!, _isActiveMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  ProductLocal map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return ProductLocal(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      rowVersion: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}row_version'])!,
      isDeleted: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_deleted'])!,
      lastModifiedHlc: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}last_modified_hlc']),
      isSynced: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_synced'])!,
      brandId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}brand_id'])!,
      categoryId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}category_id']),
      name: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}name'])!,
      description: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}description']),
      basePrice: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}base_price'])!,
      buyPrice: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}buy_price']),
      sku: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}sku']),
      barcode: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}barcode']),
      imageUrl: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}image_url']),
      stockEnabled: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}stock_enabled'])!,
      crdtPositive: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}crdt_positive'])!,
      crdtNegative: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}crdt_negative'])!,
      stockQty: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}stock_qty'])!,
      isActive: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_active'])!,
    );
  }

  @override
  $ProductsTable createAlias(String alias) {
    return $ProductsTable(attachedDatabase, alias);
  }
}

class ProductLocal extends DataClass implements Insertable<ProductLocal> {
  final String id;
  final int rowVersion;
  final bool isDeleted;
  final String? lastModifiedHlc;
  final bool isSynced;
  final String brandId;
  final String? categoryId;
  final String name;
  final String? description;
  final double basePrice;
  final double? buyPrice;
  final String? sku;
  final String? barcode;
  final String? imageUrl;
  final bool stockEnabled;
  final String crdtPositive;
  final String crdtNegative;
  final double stockQty;
  final bool isActive;
  const ProductLocal(
      {required this.id,
      required this.rowVersion,
      required this.isDeleted,
      this.lastModifiedHlc,
      required this.isSynced,
      required this.brandId,
      this.categoryId,
      required this.name,
      this.description,
      required this.basePrice,
      this.buyPrice,
      this.sku,
      this.barcode,
      this.imageUrl,
      required this.stockEnabled,
      required this.crdtPositive,
      required this.crdtNegative,
      required this.stockQty,
      required this.isActive});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['row_version'] = Variable<int>(rowVersion);
    map['is_deleted'] = Variable<bool>(isDeleted);
    if (!nullToAbsent || lastModifiedHlc != null) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc);
    }
    map['is_synced'] = Variable<bool>(isSynced);
    map['brand_id'] = Variable<String>(brandId);
    if (!nullToAbsent || categoryId != null) {
      map['category_id'] = Variable<String>(categoryId);
    }
    map['name'] = Variable<String>(name);
    if (!nullToAbsent || description != null) {
      map['description'] = Variable<String>(description);
    }
    map['base_price'] = Variable<double>(basePrice);
    if (!nullToAbsent || buyPrice != null) {
      map['buy_price'] = Variable<double>(buyPrice);
    }
    if (!nullToAbsent || sku != null) {
      map['sku'] = Variable<String>(sku);
    }
    if (!nullToAbsent || barcode != null) {
      map['barcode'] = Variable<String>(barcode);
    }
    if (!nullToAbsent || imageUrl != null) {
      map['image_url'] = Variable<String>(imageUrl);
    }
    map['stock_enabled'] = Variable<bool>(stockEnabled);
    map['crdt_positive'] = Variable<String>(crdtPositive);
    map['crdt_negative'] = Variable<String>(crdtNegative);
    map['stock_qty'] = Variable<double>(stockQty);
    map['is_active'] = Variable<bool>(isActive);
    return map;
  }

  ProductsCompanion toCompanion(bool nullToAbsent) {
    return ProductsCompanion(
      id: Value(id),
      rowVersion: Value(rowVersion),
      isDeleted: Value(isDeleted),
      lastModifiedHlc: lastModifiedHlc == null && nullToAbsent
          ? const Value.absent()
          : Value(lastModifiedHlc),
      isSynced: Value(isSynced),
      brandId: Value(brandId),
      categoryId: categoryId == null && nullToAbsent
          ? const Value.absent()
          : Value(categoryId),
      name: Value(name),
      description: description == null && nullToAbsent
          ? const Value.absent()
          : Value(description),
      basePrice: Value(basePrice),
      buyPrice: buyPrice == null && nullToAbsent
          ? const Value.absent()
          : Value(buyPrice),
      sku: sku == null && nullToAbsent ? const Value.absent() : Value(sku),
      barcode: barcode == null && nullToAbsent
          ? const Value.absent()
          : Value(barcode),
      imageUrl: imageUrl == null && nullToAbsent
          ? const Value.absent()
          : Value(imageUrl),
      stockEnabled: Value(stockEnabled),
      crdtPositive: Value(crdtPositive),
      crdtNegative: Value(crdtNegative),
      stockQty: Value(stockQty),
      isActive: Value(isActive),
    );
  }

  factory ProductLocal.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return ProductLocal(
      id: serializer.fromJson<String>(json['id']),
      rowVersion: serializer.fromJson<int>(json['rowVersion']),
      isDeleted: serializer.fromJson<bool>(json['isDeleted']),
      lastModifiedHlc: serializer.fromJson<String?>(json['lastModifiedHlc']),
      isSynced: serializer.fromJson<bool>(json['isSynced']),
      brandId: serializer.fromJson<String>(json['brandId']),
      categoryId: serializer.fromJson<String?>(json['categoryId']),
      name: serializer.fromJson<String>(json['name']),
      description: serializer.fromJson<String?>(json['description']),
      basePrice: serializer.fromJson<double>(json['basePrice']),
      buyPrice: serializer.fromJson<double?>(json['buyPrice']),
      sku: serializer.fromJson<String?>(json['sku']),
      barcode: serializer.fromJson<String?>(json['barcode']),
      imageUrl: serializer.fromJson<String?>(json['imageUrl']),
      stockEnabled: serializer.fromJson<bool>(json['stockEnabled']),
      crdtPositive: serializer.fromJson<String>(json['crdtPositive']),
      crdtNegative: serializer.fromJson<String>(json['crdtNegative']),
      stockQty: serializer.fromJson<double>(json['stockQty']),
      isActive: serializer.fromJson<bool>(json['isActive']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'rowVersion': serializer.toJson<int>(rowVersion),
      'isDeleted': serializer.toJson<bool>(isDeleted),
      'lastModifiedHlc': serializer.toJson<String?>(lastModifiedHlc),
      'isSynced': serializer.toJson<bool>(isSynced),
      'brandId': serializer.toJson<String>(brandId),
      'categoryId': serializer.toJson<String?>(categoryId),
      'name': serializer.toJson<String>(name),
      'description': serializer.toJson<String?>(description),
      'basePrice': serializer.toJson<double>(basePrice),
      'buyPrice': serializer.toJson<double?>(buyPrice),
      'sku': serializer.toJson<String?>(sku),
      'barcode': serializer.toJson<String?>(barcode),
      'imageUrl': serializer.toJson<String?>(imageUrl),
      'stockEnabled': serializer.toJson<bool>(stockEnabled),
      'crdtPositive': serializer.toJson<String>(crdtPositive),
      'crdtNegative': serializer.toJson<String>(crdtNegative),
      'stockQty': serializer.toJson<double>(stockQty),
      'isActive': serializer.toJson<bool>(isActive),
    };
  }

  ProductLocal copyWith(
          {String? id,
          int? rowVersion,
          bool? isDeleted,
          Value<String?> lastModifiedHlc = const Value.absent(),
          bool? isSynced,
          String? brandId,
          Value<String?> categoryId = const Value.absent(),
          String? name,
          Value<String?> description = const Value.absent(),
          double? basePrice,
          Value<double?> buyPrice = const Value.absent(),
          Value<String?> sku = const Value.absent(),
          Value<String?> barcode = const Value.absent(),
          Value<String?> imageUrl = const Value.absent(),
          bool? stockEnabled,
          String? crdtPositive,
          String? crdtNegative,
          double? stockQty,
          bool? isActive}) =>
      ProductLocal(
        id: id ?? this.id,
        rowVersion: rowVersion ?? this.rowVersion,
        isDeleted: isDeleted ?? this.isDeleted,
        lastModifiedHlc: lastModifiedHlc.present
            ? lastModifiedHlc.value
            : this.lastModifiedHlc,
        isSynced: isSynced ?? this.isSynced,
        brandId: brandId ?? this.brandId,
        categoryId: categoryId.present ? categoryId.value : this.categoryId,
        name: name ?? this.name,
        description: description.present ? description.value : this.description,
        basePrice: basePrice ?? this.basePrice,
        buyPrice: buyPrice.present ? buyPrice.value : this.buyPrice,
        sku: sku.present ? sku.value : this.sku,
        barcode: barcode.present ? barcode.value : this.barcode,
        imageUrl: imageUrl.present ? imageUrl.value : this.imageUrl,
        stockEnabled: stockEnabled ?? this.stockEnabled,
        crdtPositive: crdtPositive ?? this.crdtPositive,
        crdtNegative: crdtNegative ?? this.crdtNegative,
        stockQty: stockQty ?? this.stockQty,
        isActive: isActive ?? this.isActive,
      );
  ProductLocal copyWithCompanion(ProductsCompanion data) {
    return ProductLocal(
      id: data.id.present ? data.id.value : this.id,
      rowVersion:
          data.rowVersion.present ? data.rowVersion.value : this.rowVersion,
      isDeleted: data.isDeleted.present ? data.isDeleted.value : this.isDeleted,
      lastModifiedHlc: data.lastModifiedHlc.present
          ? data.lastModifiedHlc.value
          : this.lastModifiedHlc,
      isSynced: data.isSynced.present ? data.isSynced.value : this.isSynced,
      brandId: data.brandId.present ? data.brandId.value : this.brandId,
      categoryId:
          data.categoryId.present ? data.categoryId.value : this.categoryId,
      name: data.name.present ? data.name.value : this.name,
      description:
          data.description.present ? data.description.value : this.description,
      basePrice: data.basePrice.present ? data.basePrice.value : this.basePrice,
      buyPrice: data.buyPrice.present ? data.buyPrice.value : this.buyPrice,
      sku: data.sku.present ? data.sku.value : this.sku,
      barcode: data.barcode.present ? data.barcode.value : this.barcode,
      imageUrl: data.imageUrl.present ? data.imageUrl.value : this.imageUrl,
      stockEnabled: data.stockEnabled.present
          ? data.stockEnabled.value
          : this.stockEnabled,
      crdtPositive: data.crdtPositive.present
          ? data.crdtPositive.value
          : this.crdtPositive,
      crdtNegative: data.crdtNegative.present
          ? data.crdtNegative.value
          : this.crdtNegative,
      stockQty: data.stockQty.present ? data.stockQty.value : this.stockQty,
      isActive: data.isActive.present ? data.isActive.value : this.isActive,
    );
  }

  @override
  String toString() {
    return (StringBuffer('ProductLocal(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('brandId: $brandId, ')
          ..write('categoryId: $categoryId, ')
          ..write('name: $name, ')
          ..write('description: $description, ')
          ..write('basePrice: $basePrice, ')
          ..write('buyPrice: $buyPrice, ')
          ..write('sku: $sku, ')
          ..write('barcode: $barcode, ')
          ..write('imageUrl: $imageUrl, ')
          ..write('stockEnabled: $stockEnabled, ')
          ..write('crdtPositive: $crdtPositive, ')
          ..write('crdtNegative: $crdtNegative, ')
          ..write('stockQty: $stockQty, ')
          ..write('isActive: $isActive')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
      id,
      rowVersion,
      isDeleted,
      lastModifiedHlc,
      isSynced,
      brandId,
      categoryId,
      name,
      description,
      basePrice,
      buyPrice,
      sku,
      barcode,
      imageUrl,
      stockEnabled,
      crdtPositive,
      crdtNegative,
      stockQty,
      isActive);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is ProductLocal &&
          other.id == this.id &&
          other.rowVersion == this.rowVersion &&
          other.isDeleted == this.isDeleted &&
          other.lastModifiedHlc == this.lastModifiedHlc &&
          other.isSynced == this.isSynced &&
          other.brandId == this.brandId &&
          other.categoryId == this.categoryId &&
          other.name == this.name &&
          other.description == this.description &&
          other.basePrice == this.basePrice &&
          other.buyPrice == this.buyPrice &&
          other.sku == this.sku &&
          other.barcode == this.barcode &&
          other.imageUrl == this.imageUrl &&
          other.stockEnabled == this.stockEnabled &&
          other.crdtPositive == this.crdtPositive &&
          other.crdtNegative == this.crdtNegative &&
          other.stockQty == this.stockQty &&
          other.isActive == this.isActive);
}

class ProductsCompanion extends UpdateCompanion<ProductLocal> {
  final Value<String> id;
  final Value<int> rowVersion;
  final Value<bool> isDeleted;
  final Value<String?> lastModifiedHlc;
  final Value<bool> isSynced;
  final Value<String> brandId;
  final Value<String?> categoryId;
  final Value<String> name;
  final Value<String?> description;
  final Value<double> basePrice;
  final Value<double?> buyPrice;
  final Value<String?> sku;
  final Value<String?> barcode;
  final Value<String?> imageUrl;
  final Value<bool> stockEnabled;
  final Value<String> crdtPositive;
  final Value<String> crdtNegative;
  final Value<double> stockQty;
  final Value<bool> isActive;
  final Value<int> rowid;
  const ProductsCompanion({
    this.id = const Value.absent(),
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    this.brandId = const Value.absent(),
    this.categoryId = const Value.absent(),
    this.name = const Value.absent(),
    this.description = const Value.absent(),
    this.basePrice = const Value.absent(),
    this.buyPrice = const Value.absent(),
    this.sku = const Value.absent(),
    this.barcode = const Value.absent(),
    this.imageUrl = const Value.absent(),
    this.stockEnabled = const Value.absent(),
    this.crdtPositive = const Value.absent(),
    this.crdtNegative = const Value.absent(),
    this.stockQty = const Value.absent(),
    this.isActive = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  ProductsCompanion.insert({
    required String id,
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    required String brandId,
    this.categoryId = const Value.absent(),
    required String name,
    this.description = const Value.absent(),
    required double basePrice,
    this.buyPrice = const Value.absent(),
    this.sku = const Value.absent(),
    this.barcode = const Value.absent(),
    this.imageUrl = const Value.absent(),
    this.stockEnabled = const Value.absent(),
    this.crdtPositive = const Value.absent(),
    this.crdtNegative = const Value.absent(),
    this.stockQty = const Value.absent(),
    this.isActive = const Value.absent(),
    this.rowid = const Value.absent(),
  })  : id = Value(id),
        brandId = Value(brandId),
        name = Value(name),
        basePrice = Value(basePrice);
  static Insertable<ProductLocal> custom({
    Expression<String>? id,
    Expression<int>? rowVersion,
    Expression<bool>? isDeleted,
    Expression<String>? lastModifiedHlc,
    Expression<bool>? isSynced,
    Expression<String>? brandId,
    Expression<String>? categoryId,
    Expression<String>? name,
    Expression<String>? description,
    Expression<double>? basePrice,
    Expression<double>? buyPrice,
    Expression<String>? sku,
    Expression<String>? barcode,
    Expression<String>? imageUrl,
    Expression<bool>? stockEnabled,
    Expression<String>? crdtPositive,
    Expression<String>? crdtNegative,
    Expression<double>? stockQty,
    Expression<bool>? isActive,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (rowVersion != null) 'row_version': rowVersion,
      if (isDeleted != null) 'is_deleted': isDeleted,
      if (lastModifiedHlc != null) 'last_modified_hlc': lastModifiedHlc,
      if (isSynced != null) 'is_synced': isSynced,
      if (brandId != null) 'brand_id': brandId,
      if (categoryId != null) 'category_id': categoryId,
      if (name != null) 'name': name,
      if (description != null) 'description': description,
      if (basePrice != null) 'base_price': basePrice,
      if (buyPrice != null) 'buy_price': buyPrice,
      if (sku != null) 'sku': sku,
      if (barcode != null) 'barcode': barcode,
      if (imageUrl != null) 'image_url': imageUrl,
      if (stockEnabled != null) 'stock_enabled': stockEnabled,
      if (crdtPositive != null) 'crdt_positive': crdtPositive,
      if (crdtNegative != null) 'crdt_negative': crdtNegative,
      if (stockQty != null) 'stock_qty': stockQty,
      if (isActive != null) 'is_active': isActive,
      if (rowid != null) 'rowid': rowid,
    });
  }

  ProductsCompanion copyWith(
      {Value<String>? id,
      Value<int>? rowVersion,
      Value<bool>? isDeleted,
      Value<String?>? lastModifiedHlc,
      Value<bool>? isSynced,
      Value<String>? brandId,
      Value<String?>? categoryId,
      Value<String>? name,
      Value<String?>? description,
      Value<double>? basePrice,
      Value<double?>? buyPrice,
      Value<String?>? sku,
      Value<String?>? barcode,
      Value<String?>? imageUrl,
      Value<bool>? stockEnabled,
      Value<String>? crdtPositive,
      Value<String>? crdtNegative,
      Value<double>? stockQty,
      Value<bool>? isActive,
      Value<int>? rowid}) {
    return ProductsCompanion(
      id: id ?? this.id,
      rowVersion: rowVersion ?? this.rowVersion,
      isDeleted: isDeleted ?? this.isDeleted,
      lastModifiedHlc: lastModifiedHlc ?? this.lastModifiedHlc,
      isSynced: isSynced ?? this.isSynced,
      brandId: brandId ?? this.brandId,
      categoryId: categoryId ?? this.categoryId,
      name: name ?? this.name,
      description: description ?? this.description,
      basePrice: basePrice ?? this.basePrice,
      buyPrice: buyPrice ?? this.buyPrice,
      sku: sku ?? this.sku,
      barcode: barcode ?? this.barcode,
      imageUrl: imageUrl ?? this.imageUrl,
      stockEnabled: stockEnabled ?? this.stockEnabled,
      crdtPositive: crdtPositive ?? this.crdtPositive,
      crdtNegative: crdtNegative ?? this.crdtNegative,
      stockQty: stockQty ?? this.stockQty,
      isActive: isActive ?? this.isActive,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (rowVersion.present) {
      map['row_version'] = Variable<int>(rowVersion.value);
    }
    if (isDeleted.present) {
      map['is_deleted'] = Variable<bool>(isDeleted.value);
    }
    if (lastModifiedHlc.present) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc.value);
    }
    if (isSynced.present) {
      map['is_synced'] = Variable<bool>(isSynced.value);
    }
    if (brandId.present) {
      map['brand_id'] = Variable<String>(brandId.value);
    }
    if (categoryId.present) {
      map['category_id'] = Variable<String>(categoryId.value);
    }
    if (name.present) {
      map['name'] = Variable<String>(name.value);
    }
    if (description.present) {
      map['description'] = Variable<String>(description.value);
    }
    if (basePrice.present) {
      map['base_price'] = Variable<double>(basePrice.value);
    }
    if (buyPrice.present) {
      map['buy_price'] = Variable<double>(buyPrice.value);
    }
    if (sku.present) {
      map['sku'] = Variable<String>(sku.value);
    }
    if (barcode.present) {
      map['barcode'] = Variable<String>(barcode.value);
    }
    if (imageUrl.present) {
      map['image_url'] = Variable<String>(imageUrl.value);
    }
    if (stockEnabled.present) {
      map['stock_enabled'] = Variable<bool>(stockEnabled.value);
    }
    if (crdtPositive.present) {
      map['crdt_positive'] = Variable<String>(crdtPositive.value);
    }
    if (crdtNegative.present) {
      map['crdt_negative'] = Variable<String>(crdtNegative.value);
    }
    if (stockQty.present) {
      map['stock_qty'] = Variable<double>(stockQty.value);
    }
    if (isActive.present) {
      map['is_active'] = Variable<bool>(isActive.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('ProductsCompanion(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('brandId: $brandId, ')
          ..write('categoryId: $categoryId, ')
          ..write('name: $name, ')
          ..write('description: $description, ')
          ..write('basePrice: $basePrice, ')
          ..write('buyPrice: $buyPrice, ')
          ..write('sku: $sku, ')
          ..write('barcode: $barcode, ')
          ..write('imageUrl: $imageUrl, ')
          ..write('stockEnabled: $stockEnabled, ')
          ..write('crdtPositive: $crdtPositive, ')
          ..write('crdtNegative: $crdtNegative, ')
          ..write('stockQty: $stockQty, ')
          ..write('isActive: $isActive, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $OrdersTable extends Orders with TableInfo<$OrdersTable, OrderLocal> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $OrdersTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
      'id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _rowVersionMeta =
      const VerificationMeta('rowVersion');
  @override
  late final GeneratedColumn<int> rowVersion = GeneratedColumn<int>(
      'row_version', aliasedName, false,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultValue: const Constant(0));
  static const VerificationMeta _isDeletedMeta =
      const VerificationMeta('isDeleted');
  @override
  late final GeneratedColumn<bool> isDeleted = GeneratedColumn<bool>(
      'is_deleted', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_deleted" IN (0, 1))'),
      defaultValue: const Constant(false));
  static const VerificationMeta _lastModifiedHlcMeta =
      const VerificationMeta('lastModifiedHlc');
  @override
  late final GeneratedColumn<String> lastModifiedHlc = GeneratedColumn<String>(
      'last_modified_hlc', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _isSyncedMeta =
      const VerificationMeta('isSynced');
  @override
  late final GeneratedColumn<bool> isSynced = GeneratedColumn<bool>(
      'is_synced', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_synced" IN (0, 1))'),
      defaultValue: const Constant(true));
  static const VerificationMeta _outletIdMeta =
      const VerificationMeta('outletId');
  @override
  late final GeneratedColumn<String> outletId = GeneratedColumn<String>(
      'outlet_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _shiftSessionIdMeta =
      const VerificationMeta('shiftSessionId');
  @override
  late final GeneratedColumn<String> shiftSessionId = GeneratedColumn<String>(
      'shift_session_id', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _customerIdMeta =
      const VerificationMeta('customerId');
  @override
  late final GeneratedColumn<String> customerId = GeneratedColumn<String>(
      'customer_id', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _tableIdMeta =
      const VerificationMeta('tableId');
  @override
  late final GeneratedColumn<String> tableId = GeneratedColumn<String>(
      'table_id', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _userIdMeta = const VerificationMeta('userId');
  @override
  late final GeneratedColumn<String> userId = GeneratedColumn<String>(
      'user_id', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _orderNumberMeta =
      const VerificationMeta('orderNumber');
  @override
  late final GeneratedColumn<String> orderNumber = GeneratedColumn<String>(
      'order_number', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _displayNumberMeta =
      const VerificationMeta('displayNumber');
  @override
  late final GeneratedColumn<int> displayNumber = GeneratedColumn<int>(
      'display_number', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _statusMeta = const VerificationMeta('status');
  @override
  late final GeneratedColumn<String> status = GeneratedColumn<String>(
      'status', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('pending'));
  static const VerificationMeta _orderTypeMeta =
      const VerificationMeta('orderType');
  @override
  late final GeneratedColumn<String> orderType = GeneratedColumn<String>(
      'order_type', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('dine_in'));
  static const VerificationMeta _subtotalMeta =
      const VerificationMeta('subtotal');
  @override
  late final GeneratedColumn<double> subtotal = GeneratedColumn<double>(
      'subtotal', aliasedName, false,
      type: DriftSqlType.double,
      requiredDuringInsert: false,
      defaultValue: const Constant(0.0));
  static const VerificationMeta _serviceChargeAmountMeta =
      const VerificationMeta('serviceChargeAmount');
  @override
  late final GeneratedColumn<double> serviceChargeAmount =
      GeneratedColumn<double>('service_charge_amount', aliasedName, false,
          type: DriftSqlType.double,
          requiredDuringInsert: false,
          defaultValue: const Constant(0.0));
  static const VerificationMeta _taxAmountMeta =
      const VerificationMeta('taxAmount');
  @override
  late final GeneratedColumn<double> taxAmount = GeneratedColumn<double>(
      'tax_amount', aliasedName, false,
      type: DriftSqlType.double,
      requiredDuringInsert: false,
      defaultValue: const Constant(0.0));
  static const VerificationMeta _discountAmountMeta =
      const VerificationMeta('discountAmount');
  @override
  late final GeneratedColumn<double> discountAmount = GeneratedColumn<double>(
      'discount_amount', aliasedName, false,
      type: DriftSqlType.double,
      requiredDuringInsert: false,
      defaultValue: const Constant(0.0));
  static const VerificationMeta _totalAmountMeta =
      const VerificationMeta('totalAmount');
  @override
  late final GeneratedColumn<double> totalAmount = GeneratedColumn<double>(
      'total_amount', aliasedName, false,
      type: DriftSqlType.double,
      requiredDuringInsert: false,
      defaultValue: const Constant(0.0));
  static const VerificationMeta _notesMeta = const VerificationMeta('notes');
  @override
  late final GeneratedColumn<String> notes = GeneratedColumn<String>(
      'notes', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _createdAtMeta =
      const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
      'created_at', aliasedName, true,
      type: DriftSqlType.dateTime, requiredDuringInsert: false);
  static const VerificationMeta _updatedAtMeta =
      const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
      'updated_at', aliasedName, true,
      type: DriftSqlType.dateTime, requiredDuringInsert: false);
  @override
  List<GeneratedColumn> get $columns => [
        id,
        rowVersion,
        isDeleted,
        lastModifiedHlc,
        isSynced,
        outletId,
        shiftSessionId,
        customerId,
        tableId,
        userId,
        orderNumber,
        displayNumber,
        status,
        orderType,
        subtotal,
        serviceChargeAmount,
        taxAmount,
        discountAmount,
        totalAmount,
        notes,
        createdAt,
        updatedAt
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'orders';
  @override
  VerificationContext validateIntegrity(Insertable<OrderLocal> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('row_version')) {
      context.handle(
          _rowVersionMeta,
          rowVersion.isAcceptableOrUnknown(
              data['row_version']!, _rowVersionMeta));
    }
    if (data.containsKey('is_deleted')) {
      context.handle(_isDeletedMeta,
          isDeleted.isAcceptableOrUnknown(data['is_deleted']!, _isDeletedMeta));
    }
    if (data.containsKey('last_modified_hlc')) {
      context.handle(
          _lastModifiedHlcMeta,
          lastModifiedHlc.isAcceptableOrUnknown(
              data['last_modified_hlc']!, _lastModifiedHlcMeta));
    }
    if (data.containsKey('is_synced')) {
      context.handle(_isSyncedMeta,
          isSynced.isAcceptableOrUnknown(data['is_synced']!, _isSyncedMeta));
    }
    if (data.containsKey('outlet_id')) {
      context.handle(_outletIdMeta,
          outletId.isAcceptableOrUnknown(data['outlet_id']!, _outletIdMeta));
    } else if (isInserting) {
      context.missing(_outletIdMeta);
    }
    if (data.containsKey('shift_session_id')) {
      context.handle(
          _shiftSessionIdMeta,
          shiftSessionId.isAcceptableOrUnknown(
              data['shift_session_id']!, _shiftSessionIdMeta));
    }
    if (data.containsKey('customer_id')) {
      context.handle(
          _customerIdMeta,
          customerId.isAcceptableOrUnknown(
              data['customer_id']!, _customerIdMeta));
    }
    if (data.containsKey('table_id')) {
      context.handle(_tableIdMeta,
          tableId.isAcceptableOrUnknown(data['table_id']!, _tableIdMeta));
    }
    if (data.containsKey('user_id')) {
      context.handle(_userIdMeta,
          userId.isAcceptableOrUnknown(data['user_id']!, _userIdMeta));
    }
    if (data.containsKey('order_number')) {
      context.handle(
          _orderNumberMeta,
          orderNumber.isAcceptableOrUnknown(
              data['order_number']!, _orderNumberMeta));
    } else if (isInserting) {
      context.missing(_orderNumberMeta);
    }
    if (data.containsKey('display_number')) {
      context.handle(
          _displayNumberMeta,
          displayNumber.isAcceptableOrUnknown(
              data['display_number']!, _displayNumberMeta));
    } else if (isInserting) {
      context.missing(_displayNumberMeta);
    }
    if (data.containsKey('status')) {
      context.handle(_statusMeta,
          status.isAcceptableOrUnknown(data['status']!, _statusMeta));
    }
    if (data.containsKey('order_type')) {
      context.handle(_orderTypeMeta,
          orderType.isAcceptableOrUnknown(data['order_type']!, _orderTypeMeta));
    }
    if (data.containsKey('subtotal')) {
      context.handle(_subtotalMeta,
          subtotal.isAcceptableOrUnknown(data['subtotal']!, _subtotalMeta));
    }
    if (data.containsKey('service_charge_amount')) {
      context.handle(
          _serviceChargeAmountMeta,
          serviceChargeAmount.isAcceptableOrUnknown(
              data['service_charge_amount']!, _serviceChargeAmountMeta));
    }
    if (data.containsKey('tax_amount')) {
      context.handle(_taxAmountMeta,
          taxAmount.isAcceptableOrUnknown(data['tax_amount']!, _taxAmountMeta));
    }
    if (data.containsKey('discount_amount')) {
      context.handle(
          _discountAmountMeta,
          discountAmount.isAcceptableOrUnknown(
              data['discount_amount']!, _discountAmountMeta));
    }
    if (data.containsKey('total_amount')) {
      context.handle(
          _totalAmountMeta,
          totalAmount.isAcceptableOrUnknown(
              data['total_amount']!, _totalAmountMeta));
    }
    if (data.containsKey('notes')) {
      context.handle(
          _notesMeta, notes.isAcceptableOrUnknown(data['notes']!, _notesMeta));
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta,
          createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta,
          updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  OrderLocal map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return OrderLocal(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      rowVersion: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}row_version'])!,
      isDeleted: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_deleted'])!,
      lastModifiedHlc: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}last_modified_hlc']),
      isSynced: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_synced'])!,
      outletId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}outlet_id'])!,
      shiftSessionId: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}shift_session_id']),
      customerId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}customer_id']),
      tableId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}table_id']),
      userId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}user_id']),
      orderNumber: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}order_number'])!,
      displayNumber: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}display_number'])!,
      status: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}status'])!,
      orderType: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}order_type'])!,
      subtotal: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}subtotal'])!,
      serviceChargeAmount: attachedDatabase.typeMapping.read(
          DriftSqlType.double,
          data['${effectivePrefix}service_charge_amount'])!,
      taxAmount: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}tax_amount'])!,
      discountAmount: attachedDatabase.typeMapping.read(
          DriftSqlType.double, data['${effectivePrefix}discount_amount'])!,
      totalAmount: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}total_amount'])!,
      notes: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}notes']),
      createdAt: attachedDatabase.typeMapping
          .read(DriftSqlType.dateTime, data['${effectivePrefix}created_at']),
      updatedAt: attachedDatabase.typeMapping
          .read(DriftSqlType.dateTime, data['${effectivePrefix}updated_at']),
    );
  }

  @override
  $OrdersTable createAlias(String alias) {
    return $OrdersTable(attachedDatabase, alias);
  }
}

class OrderLocal extends DataClass implements Insertable<OrderLocal> {
  final String id;
  final int rowVersion;
  final bool isDeleted;
  final String? lastModifiedHlc;
  final bool isSynced;
  final String outletId;
  final String? shiftSessionId;
  final String? customerId;
  final String? tableId;
  final String? userId;
  final String orderNumber;
  final int displayNumber;
  final String status;
  final String orderType;
  final double subtotal;
  final double serviceChargeAmount;
  final double taxAmount;
  final double discountAmount;
  final double totalAmount;
  final String? notes;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  const OrderLocal(
      {required this.id,
      required this.rowVersion,
      required this.isDeleted,
      this.lastModifiedHlc,
      required this.isSynced,
      required this.outletId,
      this.shiftSessionId,
      this.customerId,
      this.tableId,
      this.userId,
      required this.orderNumber,
      required this.displayNumber,
      required this.status,
      required this.orderType,
      required this.subtotal,
      required this.serviceChargeAmount,
      required this.taxAmount,
      required this.discountAmount,
      required this.totalAmount,
      this.notes,
      this.createdAt,
      this.updatedAt});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['row_version'] = Variable<int>(rowVersion);
    map['is_deleted'] = Variable<bool>(isDeleted);
    if (!nullToAbsent || lastModifiedHlc != null) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc);
    }
    map['is_synced'] = Variable<bool>(isSynced);
    map['outlet_id'] = Variable<String>(outletId);
    if (!nullToAbsent || shiftSessionId != null) {
      map['shift_session_id'] = Variable<String>(shiftSessionId);
    }
    if (!nullToAbsent || customerId != null) {
      map['customer_id'] = Variable<String>(customerId);
    }
    if (!nullToAbsent || tableId != null) {
      map['table_id'] = Variable<String>(tableId);
    }
    if (!nullToAbsent || userId != null) {
      map['user_id'] = Variable<String>(userId);
    }
    map['order_number'] = Variable<String>(orderNumber);
    map['display_number'] = Variable<int>(displayNumber);
    map['status'] = Variable<String>(status);
    map['order_type'] = Variable<String>(orderType);
    map['subtotal'] = Variable<double>(subtotal);
    map['service_charge_amount'] = Variable<double>(serviceChargeAmount);
    map['tax_amount'] = Variable<double>(taxAmount);
    map['discount_amount'] = Variable<double>(discountAmount);
    map['total_amount'] = Variable<double>(totalAmount);
    if (!nullToAbsent || notes != null) {
      map['notes'] = Variable<String>(notes);
    }
    if (!nullToAbsent || createdAt != null) {
      map['created_at'] = Variable<DateTime>(createdAt);
    }
    if (!nullToAbsent || updatedAt != null) {
      map['updated_at'] = Variable<DateTime>(updatedAt);
    }
    return map;
  }

  OrdersCompanion toCompanion(bool nullToAbsent) {
    return OrdersCompanion(
      id: Value(id),
      rowVersion: Value(rowVersion),
      isDeleted: Value(isDeleted),
      lastModifiedHlc: lastModifiedHlc == null && nullToAbsent
          ? const Value.absent()
          : Value(lastModifiedHlc),
      isSynced: Value(isSynced),
      outletId: Value(outletId),
      shiftSessionId: shiftSessionId == null && nullToAbsent
          ? const Value.absent()
          : Value(shiftSessionId),
      customerId: customerId == null && nullToAbsent
          ? const Value.absent()
          : Value(customerId),
      tableId: tableId == null && nullToAbsent
          ? const Value.absent()
          : Value(tableId),
      userId:
          userId == null && nullToAbsent ? const Value.absent() : Value(userId),
      orderNumber: Value(orderNumber),
      displayNumber: Value(displayNumber),
      status: Value(status),
      orderType: Value(orderType),
      subtotal: Value(subtotal),
      serviceChargeAmount: Value(serviceChargeAmount),
      taxAmount: Value(taxAmount),
      discountAmount: Value(discountAmount),
      totalAmount: Value(totalAmount),
      notes:
          notes == null && nullToAbsent ? const Value.absent() : Value(notes),
      createdAt: createdAt == null && nullToAbsent
          ? const Value.absent()
          : Value(createdAt),
      updatedAt: updatedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(updatedAt),
    );
  }

  factory OrderLocal.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return OrderLocal(
      id: serializer.fromJson<String>(json['id']),
      rowVersion: serializer.fromJson<int>(json['rowVersion']),
      isDeleted: serializer.fromJson<bool>(json['isDeleted']),
      lastModifiedHlc: serializer.fromJson<String?>(json['lastModifiedHlc']),
      isSynced: serializer.fromJson<bool>(json['isSynced']),
      outletId: serializer.fromJson<String>(json['outletId']),
      shiftSessionId: serializer.fromJson<String?>(json['shiftSessionId']),
      customerId: serializer.fromJson<String?>(json['customerId']),
      tableId: serializer.fromJson<String?>(json['tableId']),
      userId: serializer.fromJson<String?>(json['userId']),
      orderNumber: serializer.fromJson<String>(json['orderNumber']),
      displayNumber: serializer.fromJson<int>(json['displayNumber']),
      status: serializer.fromJson<String>(json['status']),
      orderType: serializer.fromJson<String>(json['orderType']),
      subtotal: serializer.fromJson<double>(json['subtotal']),
      serviceChargeAmount:
          serializer.fromJson<double>(json['serviceChargeAmount']),
      taxAmount: serializer.fromJson<double>(json['taxAmount']),
      discountAmount: serializer.fromJson<double>(json['discountAmount']),
      totalAmount: serializer.fromJson<double>(json['totalAmount']),
      notes: serializer.fromJson<String?>(json['notes']),
      createdAt: serializer.fromJson<DateTime?>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime?>(json['updatedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'rowVersion': serializer.toJson<int>(rowVersion),
      'isDeleted': serializer.toJson<bool>(isDeleted),
      'lastModifiedHlc': serializer.toJson<String?>(lastModifiedHlc),
      'isSynced': serializer.toJson<bool>(isSynced),
      'outletId': serializer.toJson<String>(outletId),
      'shiftSessionId': serializer.toJson<String?>(shiftSessionId),
      'customerId': serializer.toJson<String?>(customerId),
      'tableId': serializer.toJson<String?>(tableId),
      'userId': serializer.toJson<String?>(userId),
      'orderNumber': serializer.toJson<String>(orderNumber),
      'displayNumber': serializer.toJson<int>(displayNumber),
      'status': serializer.toJson<String>(status),
      'orderType': serializer.toJson<String>(orderType),
      'subtotal': serializer.toJson<double>(subtotal),
      'serviceChargeAmount': serializer.toJson<double>(serviceChargeAmount),
      'taxAmount': serializer.toJson<double>(taxAmount),
      'discountAmount': serializer.toJson<double>(discountAmount),
      'totalAmount': serializer.toJson<double>(totalAmount),
      'notes': serializer.toJson<String?>(notes),
      'createdAt': serializer.toJson<DateTime?>(createdAt),
      'updatedAt': serializer.toJson<DateTime?>(updatedAt),
    };
  }

  OrderLocal copyWith(
          {String? id,
          int? rowVersion,
          bool? isDeleted,
          Value<String?> lastModifiedHlc = const Value.absent(),
          bool? isSynced,
          String? outletId,
          Value<String?> shiftSessionId = const Value.absent(),
          Value<String?> customerId = const Value.absent(),
          Value<String?> tableId = const Value.absent(),
          Value<String?> userId = const Value.absent(),
          String? orderNumber,
          int? displayNumber,
          String? status,
          String? orderType,
          double? subtotal,
          double? serviceChargeAmount,
          double? taxAmount,
          double? discountAmount,
          double? totalAmount,
          Value<String?> notes = const Value.absent(),
          Value<DateTime?> createdAt = const Value.absent(),
          Value<DateTime?> updatedAt = const Value.absent()}) =>
      OrderLocal(
        id: id ?? this.id,
        rowVersion: rowVersion ?? this.rowVersion,
        isDeleted: isDeleted ?? this.isDeleted,
        lastModifiedHlc: lastModifiedHlc.present
            ? lastModifiedHlc.value
            : this.lastModifiedHlc,
        isSynced: isSynced ?? this.isSynced,
        outletId: outletId ?? this.outletId,
        shiftSessionId:
            shiftSessionId.present ? shiftSessionId.value : this.shiftSessionId,
        customerId: customerId.present ? customerId.value : this.customerId,
        tableId: tableId.present ? tableId.value : this.tableId,
        userId: userId.present ? userId.value : this.userId,
        orderNumber: orderNumber ?? this.orderNumber,
        displayNumber: displayNumber ?? this.displayNumber,
        status: status ?? this.status,
        orderType: orderType ?? this.orderType,
        subtotal: subtotal ?? this.subtotal,
        serviceChargeAmount: serviceChargeAmount ?? this.serviceChargeAmount,
        taxAmount: taxAmount ?? this.taxAmount,
        discountAmount: discountAmount ?? this.discountAmount,
        totalAmount: totalAmount ?? this.totalAmount,
        notes: notes.present ? notes.value : this.notes,
        createdAt: createdAt.present ? createdAt.value : this.createdAt,
        updatedAt: updatedAt.present ? updatedAt.value : this.updatedAt,
      );
  OrderLocal copyWithCompanion(OrdersCompanion data) {
    return OrderLocal(
      id: data.id.present ? data.id.value : this.id,
      rowVersion:
          data.rowVersion.present ? data.rowVersion.value : this.rowVersion,
      isDeleted: data.isDeleted.present ? data.isDeleted.value : this.isDeleted,
      lastModifiedHlc: data.lastModifiedHlc.present
          ? data.lastModifiedHlc.value
          : this.lastModifiedHlc,
      isSynced: data.isSynced.present ? data.isSynced.value : this.isSynced,
      outletId: data.outletId.present ? data.outletId.value : this.outletId,
      shiftSessionId: data.shiftSessionId.present
          ? data.shiftSessionId.value
          : this.shiftSessionId,
      customerId:
          data.customerId.present ? data.customerId.value : this.customerId,
      tableId: data.tableId.present ? data.tableId.value : this.tableId,
      userId: data.userId.present ? data.userId.value : this.userId,
      orderNumber:
          data.orderNumber.present ? data.orderNumber.value : this.orderNumber,
      displayNumber: data.displayNumber.present
          ? data.displayNumber.value
          : this.displayNumber,
      status: data.status.present ? data.status.value : this.status,
      orderType: data.orderType.present ? data.orderType.value : this.orderType,
      subtotal: data.subtotal.present ? data.subtotal.value : this.subtotal,
      serviceChargeAmount: data.serviceChargeAmount.present
          ? data.serviceChargeAmount.value
          : this.serviceChargeAmount,
      taxAmount: data.taxAmount.present ? data.taxAmount.value : this.taxAmount,
      discountAmount: data.discountAmount.present
          ? data.discountAmount.value
          : this.discountAmount,
      totalAmount:
          data.totalAmount.present ? data.totalAmount.value : this.totalAmount,
      notes: data.notes.present ? data.notes.value : this.notes,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('OrderLocal(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('outletId: $outletId, ')
          ..write('shiftSessionId: $shiftSessionId, ')
          ..write('customerId: $customerId, ')
          ..write('tableId: $tableId, ')
          ..write('userId: $userId, ')
          ..write('orderNumber: $orderNumber, ')
          ..write('displayNumber: $displayNumber, ')
          ..write('status: $status, ')
          ..write('orderType: $orderType, ')
          ..write('subtotal: $subtotal, ')
          ..write('serviceChargeAmount: $serviceChargeAmount, ')
          ..write('taxAmount: $taxAmount, ')
          ..write('discountAmount: $discountAmount, ')
          ..write('totalAmount: $totalAmount, ')
          ..write('notes: $notes, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hashAll([
        id,
        rowVersion,
        isDeleted,
        lastModifiedHlc,
        isSynced,
        outletId,
        shiftSessionId,
        customerId,
        tableId,
        userId,
        orderNumber,
        displayNumber,
        status,
        orderType,
        subtotal,
        serviceChargeAmount,
        taxAmount,
        discountAmount,
        totalAmount,
        notes,
        createdAt,
        updatedAt
      ]);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is OrderLocal &&
          other.id == this.id &&
          other.rowVersion == this.rowVersion &&
          other.isDeleted == this.isDeleted &&
          other.lastModifiedHlc == this.lastModifiedHlc &&
          other.isSynced == this.isSynced &&
          other.outletId == this.outletId &&
          other.shiftSessionId == this.shiftSessionId &&
          other.customerId == this.customerId &&
          other.tableId == this.tableId &&
          other.userId == this.userId &&
          other.orderNumber == this.orderNumber &&
          other.displayNumber == this.displayNumber &&
          other.status == this.status &&
          other.orderType == this.orderType &&
          other.subtotal == this.subtotal &&
          other.serviceChargeAmount == this.serviceChargeAmount &&
          other.taxAmount == this.taxAmount &&
          other.discountAmount == this.discountAmount &&
          other.totalAmount == this.totalAmount &&
          other.notes == this.notes &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt);
}

class OrdersCompanion extends UpdateCompanion<OrderLocal> {
  final Value<String> id;
  final Value<int> rowVersion;
  final Value<bool> isDeleted;
  final Value<String?> lastModifiedHlc;
  final Value<bool> isSynced;
  final Value<String> outletId;
  final Value<String?> shiftSessionId;
  final Value<String?> customerId;
  final Value<String?> tableId;
  final Value<String?> userId;
  final Value<String> orderNumber;
  final Value<int> displayNumber;
  final Value<String> status;
  final Value<String> orderType;
  final Value<double> subtotal;
  final Value<double> serviceChargeAmount;
  final Value<double> taxAmount;
  final Value<double> discountAmount;
  final Value<double> totalAmount;
  final Value<String?> notes;
  final Value<DateTime?> createdAt;
  final Value<DateTime?> updatedAt;
  final Value<int> rowid;
  const OrdersCompanion({
    this.id = const Value.absent(),
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    this.outletId = const Value.absent(),
    this.shiftSessionId = const Value.absent(),
    this.customerId = const Value.absent(),
    this.tableId = const Value.absent(),
    this.userId = const Value.absent(),
    this.orderNumber = const Value.absent(),
    this.displayNumber = const Value.absent(),
    this.status = const Value.absent(),
    this.orderType = const Value.absent(),
    this.subtotal = const Value.absent(),
    this.serviceChargeAmount = const Value.absent(),
    this.taxAmount = const Value.absent(),
    this.discountAmount = const Value.absent(),
    this.totalAmount = const Value.absent(),
    this.notes = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  OrdersCompanion.insert({
    required String id,
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    required String outletId,
    this.shiftSessionId = const Value.absent(),
    this.customerId = const Value.absent(),
    this.tableId = const Value.absent(),
    this.userId = const Value.absent(),
    required String orderNumber,
    required int displayNumber,
    this.status = const Value.absent(),
    this.orderType = const Value.absent(),
    this.subtotal = const Value.absent(),
    this.serviceChargeAmount = const Value.absent(),
    this.taxAmount = const Value.absent(),
    this.discountAmount = const Value.absent(),
    this.totalAmount = const Value.absent(),
    this.notes = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.rowid = const Value.absent(),
  })  : id = Value(id),
        outletId = Value(outletId),
        orderNumber = Value(orderNumber),
        displayNumber = Value(displayNumber);
  static Insertable<OrderLocal> custom({
    Expression<String>? id,
    Expression<int>? rowVersion,
    Expression<bool>? isDeleted,
    Expression<String>? lastModifiedHlc,
    Expression<bool>? isSynced,
    Expression<String>? outletId,
    Expression<String>? shiftSessionId,
    Expression<String>? customerId,
    Expression<String>? tableId,
    Expression<String>? userId,
    Expression<String>? orderNumber,
    Expression<int>? displayNumber,
    Expression<String>? status,
    Expression<String>? orderType,
    Expression<double>? subtotal,
    Expression<double>? serviceChargeAmount,
    Expression<double>? taxAmount,
    Expression<double>? discountAmount,
    Expression<double>? totalAmount,
    Expression<String>? notes,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (rowVersion != null) 'row_version': rowVersion,
      if (isDeleted != null) 'is_deleted': isDeleted,
      if (lastModifiedHlc != null) 'last_modified_hlc': lastModifiedHlc,
      if (isSynced != null) 'is_synced': isSynced,
      if (outletId != null) 'outlet_id': outletId,
      if (shiftSessionId != null) 'shift_session_id': shiftSessionId,
      if (customerId != null) 'customer_id': customerId,
      if (tableId != null) 'table_id': tableId,
      if (userId != null) 'user_id': userId,
      if (orderNumber != null) 'order_number': orderNumber,
      if (displayNumber != null) 'display_number': displayNumber,
      if (status != null) 'status': status,
      if (orderType != null) 'order_type': orderType,
      if (subtotal != null) 'subtotal': subtotal,
      if (serviceChargeAmount != null)
        'service_charge_amount': serviceChargeAmount,
      if (taxAmount != null) 'tax_amount': taxAmount,
      if (discountAmount != null) 'discount_amount': discountAmount,
      if (totalAmount != null) 'total_amount': totalAmount,
      if (notes != null) 'notes': notes,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  OrdersCompanion copyWith(
      {Value<String>? id,
      Value<int>? rowVersion,
      Value<bool>? isDeleted,
      Value<String?>? lastModifiedHlc,
      Value<bool>? isSynced,
      Value<String>? outletId,
      Value<String?>? shiftSessionId,
      Value<String?>? customerId,
      Value<String?>? tableId,
      Value<String?>? userId,
      Value<String>? orderNumber,
      Value<int>? displayNumber,
      Value<String>? status,
      Value<String>? orderType,
      Value<double>? subtotal,
      Value<double>? serviceChargeAmount,
      Value<double>? taxAmount,
      Value<double>? discountAmount,
      Value<double>? totalAmount,
      Value<String?>? notes,
      Value<DateTime?>? createdAt,
      Value<DateTime?>? updatedAt,
      Value<int>? rowid}) {
    return OrdersCompanion(
      id: id ?? this.id,
      rowVersion: rowVersion ?? this.rowVersion,
      isDeleted: isDeleted ?? this.isDeleted,
      lastModifiedHlc: lastModifiedHlc ?? this.lastModifiedHlc,
      isSynced: isSynced ?? this.isSynced,
      outletId: outletId ?? this.outletId,
      shiftSessionId: shiftSessionId ?? this.shiftSessionId,
      customerId: customerId ?? this.customerId,
      tableId: tableId ?? this.tableId,
      userId: userId ?? this.userId,
      orderNumber: orderNumber ?? this.orderNumber,
      displayNumber: displayNumber ?? this.displayNumber,
      status: status ?? this.status,
      orderType: orderType ?? this.orderType,
      subtotal: subtotal ?? this.subtotal,
      serviceChargeAmount: serviceChargeAmount ?? this.serviceChargeAmount,
      taxAmount: taxAmount ?? this.taxAmount,
      discountAmount: discountAmount ?? this.discountAmount,
      totalAmount: totalAmount ?? this.totalAmount,
      notes: notes ?? this.notes,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (rowVersion.present) {
      map['row_version'] = Variable<int>(rowVersion.value);
    }
    if (isDeleted.present) {
      map['is_deleted'] = Variable<bool>(isDeleted.value);
    }
    if (lastModifiedHlc.present) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc.value);
    }
    if (isSynced.present) {
      map['is_synced'] = Variable<bool>(isSynced.value);
    }
    if (outletId.present) {
      map['outlet_id'] = Variable<String>(outletId.value);
    }
    if (shiftSessionId.present) {
      map['shift_session_id'] = Variable<String>(shiftSessionId.value);
    }
    if (customerId.present) {
      map['customer_id'] = Variable<String>(customerId.value);
    }
    if (tableId.present) {
      map['table_id'] = Variable<String>(tableId.value);
    }
    if (userId.present) {
      map['user_id'] = Variable<String>(userId.value);
    }
    if (orderNumber.present) {
      map['order_number'] = Variable<String>(orderNumber.value);
    }
    if (displayNumber.present) {
      map['display_number'] = Variable<int>(displayNumber.value);
    }
    if (status.present) {
      map['status'] = Variable<String>(status.value);
    }
    if (orderType.present) {
      map['order_type'] = Variable<String>(orderType.value);
    }
    if (subtotal.present) {
      map['subtotal'] = Variable<double>(subtotal.value);
    }
    if (serviceChargeAmount.present) {
      map['service_charge_amount'] =
          Variable<double>(serviceChargeAmount.value);
    }
    if (taxAmount.present) {
      map['tax_amount'] = Variable<double>(taxAmount.value);
    }
    if (discountAmount.present) {
      map['discount_amount'] = Variable<double>(discountAmount.value);
    }
    if (totalAmount.present) {
      map['total_amount'] = Variable<double>(totalAmount.value);
    }
    if (notes.present) {
      map['notes'] = Variable<String>(notes.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('OrdersCompanion(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('outletId: $outletId, ')
          ..write('shiftSessionId: $shiftSessionId, ')
          ..write('customerId: $customerId, ')
          ..write('tableId: $tableId, ')
          ..write('userId: $userId, ')
          ..write('orderNumber: $orderNumber, ')
          ..write('displayNumber: $displayNumber, ')
          ..write('status: $status, ')
          ..write('orderType: $orderType, ')
          ..write('subtotal: $subtotal, ')
          ..write('serviceChargeAmount: $serviceChargeAmount, ')
          ..write('taxAmount: $taxAmount, ')
          ..write('discountAmount: $discountAmount, ')
          ..write('totalAmount: $totalAmount, ')
          ..write('notes: $notes, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $OrderItemsTable extends OrderItems
    with TableInfo<$OrderItemsTable, OrderItemLocal> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $OrderItemsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
      'id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _rowVersionMeta =
      const VerificationMeta('rowVersion');
  @override
  late final GeneratedColumn<int> rowVersion = GeneratedColumn<int>(
      'row_version', aliasedName, false,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultValue: const Constant(0));
  static const VerificationMeta _isDeletedMeta =
      const VerificationMeta('isDeleted');
  @override
  late final GeneratedColumn<bool> isDeleted = GeneratedColumn<bool>(
      'is_deleted', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_deleted" IN (0, 1))'),
      defaultValue: const Constant(false));
  static const VerificationMeta _lastModifiedHlcMeta =
      const VerificationMeta('lastModifiedHlc');
  @override
  late final GeneratedColumn<String> lastModifiedHlc = GeneratedColumn<String>(
      'last_modified_hlc', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _isSyncedMeta =
      const VerificationMeta('isSynced');
  @override
  late final GeneratedColumn<bool> isSynced = GeneratedColumn<bool>(
      'is_synced', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_synced" IN (0, 1))'),
      defaultValue: const Constant(true));
  static const VerificationMeta _orderIdMeta =
      const VerificationMeta('orderId');
  @override
  late final GeneratedColumn<String> orderId = GeneratedColumn<String>(
      'order_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _productIdMeta =
      const VerificationMeta('productId');
  @override
  late final GeneratedColumn<String> productId = GeneratedColumn<String>(
      'product_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _productVariantIdMeta =
      const VerificationMeta('productVariantId');
  @override
  late final GeneratedColumn<String> productVariantId = GeneratedColumn<String>(
      'product_variant_id', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _quantityMeta =
      const VerificationMeta('quantity');
  @override
  late final GeneratedColumn<int> quantity = GeneratedColumn<int>(
      'quantity', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _unitPriceMeta =
      const VerificationMeta('unitPrice');
  @override
  late final GeneratedColumn<double> unitPrice = GeneratedColumn<double>(
      'unit_price', aliasedName, false,
      type: DriftSqlType.double, requiredDuringInsert: true);
  static const VerificationMeta _discountAmountMeta =
      const VerificationMeta('discountAmount');
  @override
  late final GeneratedColumn<double> discountAmount = GeneratedColumn<double>(
      'discount_amount', aliasedName, false,
      type: DriftSqlType.double,
      requiredDuringInsert: false,
      defaultValue: const Constant(0.0));
  static const VerificationMeta _totalPriceMeta =
      const VerificationMeta('totalPrice');
  @override
  late final GeneratedColumn<double> totalPrice = GeneratedColumn<double>(
      'total_price', aliasedName, false,
      type: DriftSqlType.double, requiredDuringInsert: true);
  static const VerificationMeta _modifiersMeta =
      const VerificationMeta('modifiers');
  @override
  late final GeneratedColumn<String> modifiers = GeneratedColumn<String>(
      'modifiers', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _notesMeta = const VerificationMeta('notes');
  @override
  late final GeneratedColumn<String> notes = GeneratedColumn<String>(
      'notes', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _paidAtMeta = const VerificationMeta('paidAt');
  @override
  late final GeneratedColumn<DateTime> paidAt = GeneratedColumn<DateTime>(
      'paid_at', aliasedName, true,
      type: DriftSqlType.dateTime, requiredDuringInsert: false);
  static const VerificationMeta _paidPaymentIdMeta =
      const VerificationMeta('paidPaymentId');
  @override
  late final GeneratedColumn<String> paidPaymentId = GeneratedColumn<String>(
      'paid_payment_id', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  @override
  List<GeneratedColumn> get $columns => [
        id,
        rowVersion,
        isDeleted,
        lastModifiedHlc,
        isSynced,
        orderId,
        productId,
        productVariantId,
        quantity,
        unitPrice,
        discountAmount,
        totalPrice,
        modifiers,
        notes,
        paidAt,
        paidPaymentId
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'order_items';
  @override
  VerificationContext validateIntegrity(Insertable<OrderItemLocal> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('row_version')) {
      context.handle(
          _rowVersionMeta,
          rowVersion.isAcceptableOrUnknown(
              data['row_version']!, _rowVersionMeta));
    }
    if (data.containsKey('is_deleted')) {
      context.handle(_isDeletedMeta,
          isDeleted.isAcceptableOrUnknown(data['is_deleted']!, _isDeletedMeta));
    }
    if (data.containsKey('last_modified_hlc')) {
      context.handle(
          _lastModifiedHlcMeta,
          lastModifiedHlc.isAcceptableOrUnknown(
              data['last_modified_hlc']!, _lastModifiedHlcMeta));
    }
    if (data.containsKey('is_synced')) {
      context.handle(_isSyncedMeta,
          isSynced.isAcceptableOrUnknown(data['is_synced']!, _isSyncedMeta));
    }
    if (data.containsKey('order_id')) {
      context.handle(_orderIdMeta,
          orderId.isAcceptableOrUnknown(data['order_id']!, _orderIdMeta));
    } else if (isInserting) {
      context.missing(_orderIdMeta);
    }
    if (data.containsKey('product_id')) {
      context.handle(_productIdMeta,
          productId.isAcceptableOrUnknown(data['product_id']!, _productIdMeta));
    } else if (isInserting) {
      context.missing(_productIdMeta);
    }
    if (data.containsKey('product_variant_id')) {
      context.handle(
          _productVariantIdMeta,
          productVariantId.isAcceptableOrUnknown(
              data['product_variant_id']!, _productVariantIdMeta));
    }
    if (data.containsKey('quantity')) {
      context.handle(_quantityMeta,
          quantity.isAcceptableOrUnknown(data['quantity']!, _quantityMeta));
    } else if (isInserting) {
      context.missing(_quantityMeta);
    }
    if (data.containsKey('unit_price')) {
      context.handle(_unitPriceMeta,
          unitPrice.isAcceptableOrUnknown(data['unit_price']!, _unitPriceMeta));
    } else if (isInserting) {
      context.missing(_unitPriceMeta);
    }
    if (data.containsKey('discount_amount')) {
      context.handle(
          _discountAmountMeta,
          discountAmount.isAcceptableOrUnknown(
              data['discount_amount']!, _discountAmountMeta));
    }
    if (data.containsKey('total_price')) {
      context.handle(
          _totalPriceMeta,
          totalPrice.isAcceptableOrUnknown(
              data['total_price']!, _totalPriceMeta));
    } else if (isInserting) {
      context.missing(_totalPriceMeta);
    }
    if (data.containsKey('modifiers')) {
      context.handle(_modifiersMeta,
          modifiers.isAcceptableOrUnknown(data['modifiers']!, _modifiersMeta));
    }
    if (data.containsKey('notes')) {
      context.handle(
          _notesMeta, notes.isAcceptableOrUnknown(data['notes']!, _notesMeta));
    }
    if (data.containsKey('paid_at')) {
      context.handle(_paidAtMeta,
          paidAt.isAcceptableOrUnknown(data['paid_at']!, _paidAtMeta));
    }
    if (data.containsKey('paid_payment_id')) {
      context.handle(
          _paidPaymentIdMeta,
          paidPaymentId.isAcceptableOrUnknown(
              data['paid_payment_id']!, _paidPaymentIdMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  OrderItemLocal map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return OrderItemLocal(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      rowVersion: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}row_version'])!,
      isDeleted: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_deleted'])!,
      lastModifiedHlc: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}last_modified_hlc']),
      isSynced: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_synced'])!,
      orderId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}order_id'])!,
      productId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}product_id'])!,
      productVariantId: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}product_variant_id']),
      quantity: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}quantity'])!,
      unitPrice: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}unit_price'])!,
      discountAmount: attachedDatabase.typeMapping.read(
          DriftSqlType.double, data['${effectivePrefix}discount_amount'])!,
      totalPrice: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}total_price'])!,
      modifiers: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}modifiers']),
      notes: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}notes']),
      paidAt: attachedDatabase.typeMapping
          .read(DriftSqlType.dateTime, data['${effectivePrefix}paid_at']),
      paidPaymentId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}paid_payment_id']),
    );
  }

  @override
  $OrderItemsTable createAlias(String alias) {
    return $OrderItemsTable(attachedDatabase, alias);
  }
}

class OrderItemLocal extends DataClass implements Insertable<OrderItemLocal> {
  final String id;
  final int rowVersion;
  final bool isDeleted;
  final String? lastModifiedHlc;
  final bool isSynced;
  final String orderId;
  final String productId;
  final String? productVariantId;
  final int quantity;
  final double unitPrice;
  final double discountAmount;
  final double totalPrice;
  final String? modifiers;
  final String? notes;
  final DateTime? paidAt;
  final String? paidPaymentId;
  const OrderItemLocal(
      {required this.id,
      required this.rowVersion,
      required this.isDeleted,
      this.lastModifiedHlc,
      required this.isSynced,
      required this.orderId,
      required this.productId,
      this.productVariantId,
      required this.quantity,
      required this.unitPrice,
      required this.discountAmount,
      required this.totalPrice,
      this.modifiers,
      this.notes,
      this.paidAt,
      this.paidPaymentId});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['row_version'] = Variable<int>(rowVersion);
    map['is_deleted'] = Variable<bool>(isDeleted);
    if (!nullToAbsent || lastModifiedHlc != null) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc);
    }
    map['is_synced'] = Variable<bool>(isSynced);
    map['order_id'] = Variable<String>(orderId);
    map['product_id'] = Variable<String>(productId);
    if (!nullToAbsent || productVariantId != null) {
      map['product_variant_id'] = Variable<String>(productVariantId);
    }
    map['quantity'] = Variable<int>(quantity);
    map['unit_price'] = Variable<double>(unitPrice);
    map['discount_amount'] = Variable<double>(discountAmount);
    map['total_price'] = Variable<double>(totalPrice);
    if (!nullToAbsent || modifiers != null) {
      map['modifiers'] = Variable<String>(modifiers);
    }
    if (!nullToAbsent || notes != null) {
      map['notes'] = Variable<String>(notes);
    }
    if (!nullToAbsent || paidAt != null) {
      map['paid_at'] = Variable<DateTime>(paidAt);
    }
    if (!nullToAbsent || paidPaymentId != null) {
      map['paid_payment_id'] = Variable<String>(paidPaymentId);
    }
    return map;
  }

  OrderItemsCompanion toCompanion(bool nullToAbsent) {
    return OrderItemsCompanion(
      id: Value(id),
      rowVersion: Value(rowVersion),
      isDeleted: Value(isDeleted),
      lastModifiedHlc: lastModifiedHlc == null && nullToAbsent
          ? const Value.absent()
          : Value(lastModifiedHlc),
      isSynced: Value(isSynced),
      orderId: Value(orderId),
      productId: Value(productId),
      productVariantId: productVariantId == null && nullToAbsent
          ? const Value.absent()
          : Value(productVariantId),
      quantity: Value(quantity),
      unitPrice: Value(unitPrice),
      discountAmount: Value(discountAmount),
      totalPrice: Value(totalPrice),
      modifiers: modifiers == null && nullToAbsent
          ? const Value.absent()
          : Value(modifiers),
      notes:
          notes == null && nullToAbsent ? const Value.absent() : Value(notes),
      paidAt:
          paidAt == null && nullToAbsent ? const Value.absent() : Value(paidAt),
      paidPaymentId: paidPaymentId == null && nullToAbsent
          ? const Value.absent()
          : Value(paidPaymentId),
    );
  }

  factory OrderItemLocal.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return OrderItemLocal(
      id: serializer.fromJson<String>(json['id']),
      rowVersion: serializer.fromJson<int>(json['rowVersion']),
      isDeleted: serializer.fromJson<bool>(json['isDeleted']),
      lastModifiedHlc: serializer.fromJson<String?>(json['lastModifiedHlc']),
      isSynced: serializer.fromJson<bool>(json['isSynced']),
      orderId: serializer.fromJson<String>(json['orderId']),
      productId: serializer.fromJson<String>(json['productId']),
      productVariantId: serializer.fromJson<String?>(json['productVariantId']),
      quantity: serializer.fromJson<int>(json['quantity']),
      unitPrice: serializer.fromJson<double>(json['unitPrice']),
      discountAmount: serializer.fromJson<double>(json['discountAmount']),
      totalPrice: serializer.fromJson<double>(json['totalPrice']),
      modifiers: serializer.fromJson<String?>(json['modifiers']),
      notes: serializer.fromJson<String?>(json['notes']),
      paidAt: serializer.fromJson<DateTime?>(json['paidAt']),
      paidPaymentId: serializer.fromJson<String?>(json['paidPaymentId']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'rowVersion': serializer.toJson<int>(rowVersion),
      'isDeleted': serializer.toJson<bool>(isDeleted),
      'lastModifiedHlc': serializer.toJson<String?>(lastModifiedHlc),
      'isSynced': serializer.toJson<bool>(isSynced),
      'orderId': serializer.toJson<String>(orderId),
      'productId': serializer.toJson<String>(productId),
      'productVariantId': serializer.toJson<String?>(productVariantId),
      'quantity': serializer.toJson<int>(quantity),
      'unitPrice': serializer.toJson<double>(unitPrice),
      'discountAmount': serializer.toJson<double>(discountAmount),
      'totalPrice': serializer.toJson<double>(totalPrice),
      'modifiers': serializer.toJson<String?>(modifiers),
      'notes': serializer.toJson<String?>(notes),
      'paidAt': serializer.toJson<DateTime?>(paidAt),
      'paidPaymentId': serializer.toJson<String?>(paidPaymentId),
    };
  }

  OrderItemLocal copyWith(
          {String? id,
          int? rowVersion,
          bool? isDeleted,
          Value<String?> lastModifiedHlc = const Value.absent(),
          bool? isSynced,
          String? orderId,
          String? productId,
          Value<String?> productVariantId = const Value.absent(),
          int? quantity,
          double? unitPrice,
          double? discountAmount,
          double? totalPrice,
          Value<String?> modifiers = const Value.absent(),
          Value<String?> notes = const Value.absent(),
          Value<DateTime?> paidAt = const Value.absent(),
          Value<String?> paidPaymentId = const Value.absent()}) =>
      OrderItemLocal(
        id: id ?? this.id,
        rowVersion: rowVersion ?? this.rowVersion,
        isDeleted: isDeleted ?? this.isDeleted,
        lastModifiedHlc: lastModifiedHlc.present
            ? lastModifiedHlc.value
            : this.lastModifiedHlc,
        isSynced: isSynced ?? this.isSynced,
        orderId: orderId ?? this.orderId,
        productId: productId ?? this.productId,
        productVariantId: productVariantId.present
            ? productVariantId.value
            : this.productVariantId,
        quantity: quantity ?? this.quantity,
        unitPrice: unitPrice ?? this.unitPrice,
        discountAmount: discountAmount ?? this.discountAmount,
        totalPrice: totalPrice ?? this.totalPrice,
        modifiers: modifiers.present ? modifiers.value : this.modifiers,
        notes: notes.present ? notes.value : this.notes,
        paidAt: paidAt.present ? paidAt.value : this.paidAt,
        paidPaymentId:
            paidPaymentId.present ? paidPaymentId.value : this.paidPaymentId,
      );
  OrderItemLocal copyWithCompanion(OrderItemsCompanion data) {
    return OrderItemLocal(
      id: data.id.present ? data.id.value : this.id,
      rowVersion:
          data.rowVersion.present ? data.rowVersion.value : this.rowVersion,
      isDeleted: data.isDeleted.present ? data.isDeleted.value : this.isDeleted,
      lastModifiedHlc: data.lastModifiedHlc.present
          ? data.lastModifiedHlc.value
          : this.lastModifiedHlc,
      isSynced: data.isSynced.present ? data.isSynced.value : this.isSynced,
      orderId: data.orderId.present ? data.orderId.value : this.orderId,
      productId: data.productId.present ? data.productId.value : this.productId,
      productVariantId: data.productVariantId.present
          ? data.productVariantId.value
          : this.productVariantId,
      quantity: data.quantity.present ? data.quantity.value : this.quantity,
      unitPrice: data.unitPrice.present ? data.unitPrice.value : this.unitPrice,
      discountAmount: data.discountAmount.present
          ? data.discountAmount.value
          : this.discountAmount,
      totalPrice:
          data.totalPrice.present ? data.totalPrice.value : this.totalPrice,
      modifiers: data.modifiers.present ? data.modifiers.value : this.modifiers,
      notes: data.notes.present ? data.notes.value : this.notes,
      paidAt: data.paidAt.present ? data.paidAt.value : this.paidAt,
      paidPaymentId: data.paidPaymentId.present
          ? data.paidPaymentId.value
          : this.paidPaymentId,
    );
  }

  @override
  String toString() {
    return (StringBuffer('OrderItemLocal(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('orderId: $orderId, ')
          ..write('productId: $productId, ')
          ..write('productVariantId: $productVariantId, ')
          ..write('quantity: $quantity, ')
          ..write('unitPrice: $unitPrice, ')
          ..write('discountAmount: $discountAmount, ')
          ..write('totalPrice: $totalPrice, ')
          ..write('modifiers: $modifiers, ')
          ..write('notes: $notes, ')
          ..write('paidAt: $paidAt, ')
          ..write('paidPaymentId: $paidPaymentId')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
      id,
      rowVersion,
      isDeleted,
      lastModifiedHlc,
      isSynced,
      orderId,
      productId,
      productVariantId,
      quantity,
      unitPrice,
      discountAmount,
      totalPrice,
      modifiers,
      notes,
      paidAt,
      paidPaymentId);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is OrderItemLocal &&
          other.id == this.id &&
          other.rowVersion == this.rowVersion &&
          other.isDeleted == this.isDeleted &&
          other.lastModifiedHlc == this.lastModifiedHlc &&
          other.isSynced == this.isSynced &&
          other.orderId == this.orderId &&
          other.productId == this.productId &&
          other.productVariantId == this.productVariantId &&
          other.quantity == this.quantity &&
          other.unitPrice == this.unitPrice &&
          other.discountAmount == this.discountAmount &&
          other.totalPrice == this.totalPrice &&
          other.modifiers == this.modifiers &&
          other.notes == this.notes &&
          other.paidAt == this.paidAt &&
          other.paidPaymentId == this.paidPaymentId);
}

class OrderItemsCompanion extends UpdateCompanion<OrderItemLocal> {
  final Value<String> id;
  final Value<int> rowVersion;
  final Value<bool> isDeleted;
  final Value<String?> lastModifiedHlc;
  final Value<bool> isSynced;
  final Value<String> orderId;
  final Value<String> productId;
  final Value<String?> productVariantId;
  final Value<int> quantity;
  final Value<double> unitPrice;
  final Value<double> discountAmount;
  final Value<double> totalPrice;
  final Value<String?> modifiers;
  final Value<String?> notes;
  final Value<DateTime?> paidAt;
  final Value<String?> paidPaymentId;
  final Value<int> rowid;
  const OrderItemsCompanion({
    this.id = const Value.absent(),
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    this.orderId = const Value.absent(),
    this.productId = const Value.absent(),
    this.productVariantId = const Value.absent(),
    this.quantity = const Value.absent(),
    this.unitPrice = const Value.absent(),
    this.discountAmount = const Value.absent(),
    this.totalPrice = const Value.absent(),
    this.modifiers = const Value.absent(),
    this.notes = const Value.absent(),
    this.paidAt = const Value.absent(),
    this.paidPaymentId = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  OrderItemsCompanion.insert({
    required String id,
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    required String orderId,
    required String productId,
    this.productVariantId = const Value.absent(),
    required int quantity,
    required double unitPrice,
    this.discountAmount = const Value.absent(),
    required double totalPrice,
    this.modifiers = const Value.absent(),
    this.notes = const Value.absent(),
    this.paidAt = const Value.absent(),
    this.paidPaymentId = const Value.absent(),
    this.rowid = const Value.absent(),
  })  : id = Value(id),
        orderId = Value(orderId),
        productId = Value(productId),
        quantity = Value(quantity),
        unitPrice = Value(unitPrice),
        totalPrice = Value(totalPrice);
  static Insertable<OrderItemLocal> custom({
    Expression<String>? id,
    Expression<int>? rowVersion,
    Expression<bool>? isDeleted,
    Expression<String>? lastModifiedHlc,
    Expression<bool>? isSynced,
    Expression<String>? orderId,
    Expression<String>? productId,
    Expression<String>? productVariantId,
    Expression<int>? quantity,
    Expression<double>? unitPrice,
    Expression<double>? discountAmount,
    Expression<double>? totalPrice,
    Expression<String>? modifiers,
    Expression<String>? notes,
    Expression<DateTime>? paidAt,
    Expression<String>? paidPaymentId,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (rowVersion != null) 'row_version': rowVersion,
      if (isDeleted != null) 'is_deleted': isDeleted,
      if (lastModifiedHlc != null) 'last_modified_hlc': lastModifiedHlc,
      if (isSynced != null) 'is_synced': isSynced,
      if (orderId != null) 'order_id': orderId,
      if (productId != null) 'product_id': productId,
      if (productVariantId != null) 'product_variant_id': productVariantId,
      if (quantity != null) 'quantity': quantity,
      if (unitPrice != null) 'unit_price': unitPrice,
      if (discountAmount != null) 'discount_amount': discountAmount,
      if (totalPrice != null) 'total_price': totalPrice,
      if (modifiers != null) 'modifiers': modifiers,
      if (notes != null) 'notes': notes,
      if (paidAt != null) 'paid_at': paidAt,
      if (paidPaymentId != null) 'paid_payment_id': paidPaymentId,
      if (rowid != null) 'rowid': rowid,
    });
  }

  OrderItemsCompanion copyWith(
      {Value<String>? id,
      Value<int>? rowVersion,
      Value<bool>? isDeleted,
      Value<String?>? lastModifiedHlc,
      Value<bool>? isSynced,
      Value<String>? orderId,
      Value<String>? productId,
      Value<String?>? productVariantId,
      Value<int>? quantity,
      Value<double>? unitPrice,
      Value<double>? discountAmount,
      Value<double>? totalPrice,
      Value<String?>? modifiers,
      Value<String?>? notes,
      Value<DateTime?>? paidAt,
      Value<String?>? paidPaymentId,
      Value<int>? rowid}) {
    return OrderItemsCompanion(
      id: id ?? this.id,
      rowVersion: rowVersion ?? this.rowVersion,
      isDeleted: isDeleted ?? this.isDeleted,
      lastModifiedHlc: lastModifiedHlc ?? this.lastModifiedHlc,
      isSynced: isSynced ?? this.isSynced,
      orderId: orderId ?? this.orderId,
      productId: productId ?? this.productId,
      productVariantId: productVariantId ?? this.productVariantId,
      quantity: quantity ?? this.quantity,
      unitPrice: unitPrice ?? this.unitPrice,
      discountAmount: discountAmount ?? this.discountAmount,
      totalPrice: totalPrice ?? this.totalPrice,
      modifiers: modifiers ?? this.modifiers,
      notes: notes ?? this.notes,
      paidAt: paidAt ?? this.paidAt,
      paidPaymentId: paidPaymentId ?? this.paidPaymentId,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (rowVersion.present) {
      map['row_version'] = Variable<int>(rowVersion.value);
    }
    if (isDeleted.present) {
      map['is_deleted'] = Variable<bool>(isDeleted.value);
    }
    if (lastModifiedHlc.present) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc.value);
    }
    if (isSynced.present) {
      map['is_synced'] = Variable<bool>(isSynced.value);
    }
    if (orderId.present) {
      map['order_id'] = Variable<String>(orderId.value);
    }
    if (productId.present) {
      map['product_id'] = Variable<String>(productId.value);
    }
    if (productVariantId.present) {
      map['product_variant_id'] = Variable<String>(productVariantId.value);
    }
    if (quantity.present) {
      map['quantity'] = Variable<int>(quantity.value);
    }
    if (unitPrice.present) {
      map['unit_price'] = Variable<double>(unitPrice.value);
    }
    if (discountAmount.present) {
      map['discount_amount'] = Variable<double>(discountAmount.value);
    }
    if (totalPrice.present) {
      map['total_price'] = Variable<double>(totalPrice.value);
    }
    if (modifiers.present) {
      map['modifiers'] = Variable<String>(modifiers.value);
    }
    if (notes.present) {
      map['notes'] = Variable<String>(notes.value);
    }
    if (paidAt.present) {
      map['paid_at'] = Variable<DateTime>(paidAt.value);
    }
    if (paidPaymentId.present) {
      map['paid_payment_id'] = Variable<String>(paidPaymentId.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('OrderItemsCompanion(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('orderId: $orderId, ')
          ..write('productId: $productId, ')
          ..write('productVariantId: $productVariantId, ')
          ..write('quantity: $quantity, ')
          ..write('unitPrice: $unitPrice, ')
          ..write('discountAmount: $discountAmount, ')
          ..write('totalPrice: $totalPrice, ')
          ..write('modifiers: $modifiers, ')
          ..write('notes: $notes, ')
          ..write('paidAt: $paidAt, ')
          ..write('paidPaymentId: $paidPaymentId, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $PaymentsTable extends Payments
    with TableInfo<$PaymentsTable, PaymentLocal> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $PaymentsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
      'id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _rowVersionMeta =
      const VerificationMeta('rowVersion');
  @override
  late final GeneratedColumn<int> rowVersion = GeneratedColumn<int>(
      'row_version', aliasedName, false,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultValue: const Constant(0));
  static const VerificationMeta _isDeletedMeta =
      const VerificationMeta('isDeleted');
  @override
  late final GeneratedColumn<bool> isDeleted = GeneratedColumn<bool>(
      'is_deleted', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_deleted" IN (0, 1))'),
      defaultValue: const Constant(false));
  static const VerificationMeta _lastModifiedHlcMeta =
      const VerificationMeta('lastModifiedHlc');
  @override
  late final GeneratedColumn<String> lastModifiedHlc = GeneratedColumn<String>(
      'last_modified_hlc', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _isSyncedMeta =
      const VerificationMeta('isSynced');
  @override
  late final GeneratedColumn<bool> isSynced = GeneratedColumn<bool>(
      'is_synced', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_synced" IN (0, 1))'),
      defaultValue: const Constant(true));
  static const VerificationMeta _orderIdMeta =
      const VerificationMeta('orderId');
  @override
  late final GeneratedColumn<String> orderId = GeneratedColumn<String>(
      'order_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _outletIdMeta =
      const VerificationMeta('outletId');
  @override
  late final GeneratedColumn<String> outletId = GeneratedColumn<String>(
      'outlet_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _shiftSessionIdMeta =
      const VerificationMeta('shiftSessionId');
  @override
  late final GeneratedColumn<String> shiftSessionId = GeneratedColumn<String>(
      'shift_session_id', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _amountDueMeta =
      const VerificationMeta('amountDue');
  @override
  late final GeneratedColumn<double> amountDue = GeneratedColumn<double>(
      'amount_due', aliasedName, false,
      type: DriftSqlType.double, requiredDuringInsert: true);
  static const VerificationMeta _amountPaidMeta =
      const VerificationMeta('amountPaid');
  @override
  late final GeneratedColumn<double> amountPaid = GeneratedColumn<double>(
      'amount_paid', aliasedName, false,
      type: DriftSqlType.double, requiredDuringInsert: true);
  static const VerificationMeta _paymentMethodMeta =
      const VerificationMeta('paymentMethod');
  @override
  late final GeneratedColumn<String> paymentMethod = GeneratedColumn<String>(
      'payment_method', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _statusMeta = const VerificationMeta('status');
  @override
  late final GeneratedColumn<String> status = GeneratedColumn<String>(
      'status', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('pending'));
  static const VerificationMeta _referenceNumberMeta =
      const VerificationMeta('referenceNumber');
  @override
  late final GeneratedColumn<String> referenceNumber = GeneratedColumn<String>(
      'reference_number', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _paidAtMeta = const VerificationMeta('paidAt');
  @override
  late final GeneratedColumn<DateTime> paidAt = GeneratedColumn<DateTime>(
      'paid_at', aliasedName, true,
      type: DriftSqlType.dateTime, requiredDuringInsert: false);
  @override
  List<GeneratedColumn> get $columns => [
        id,
        rowVersion,
        isDeleted,
        lastModifiedHlc,
        isSynced,
        orderId,
        outletId,
        shiftSessionId,
        amountDue,
        amountPaid,
        paymentMethod,
        status,
        referenceNumber,
        paidAt
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'payments';
  @override
  VerificationContext validateIntegrity(Insertable<PaymentLocal> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('row_version')) {
      context.handle(
          _rowVersionMeta,
          rowVersion.isAcceptableOrUnknown(
              data['row_version']!, _rowVersionMeta));
    }
    if (data.containsKey('is_deleted')) {
      context.handle(_isDeletedMeta,
          isDeleted.isAcceptableOrUnknown(data['is_deleted']!, _isDeletedMeta));
    }
    if (data.containsKey('last_modified_hlc')) {
      context.handle(
          _lastModifiedHlcMeta,
          lastModifiedHlc.isAcceptableOrUnknown(
              data['last_modified_hlc']!, _lastModifiedHlcMeta));
    }
    if (data.containsKey('is_synced')) {
      context.handle(_isSyncedMeta,
          isSynced.isAcceptableOrUnknown(data['is_synced']!, _isSyncedMeta));
    }
    if (data.containsKey('order_id')) {
      context.handle(_orderIdMeta,
          orderId.isAcceptableOrUnknown(data['order_id']!, _orderIdMeta));
    } else if (isInserting) {
      context.missing(_orderIdMeta);
    }
    if (data.containsKey('outlet_id')) {
      context.handle(_outletIdMeta,
          outletId.isAcceptableOrUnknown(data['outlet_id']!, _outletIdMeta));
    } else if (isInserting) {
      context.missing(_outletIdMeta);
    }
    if (data.containsKey('shift_session_id')) {
      context.handle(
          _shiftSessionIdMeta,
          shiftSessionId.isAcceptableOrUnknown(
              data['shift_session_id']!, _shiftSessionIdMeta));
    }
    if (data.containsKey('amount_due')) {
      context.handle(_amountDueMeta,
          amountDue.isAcceptableOrUnknown(data['amount_due']!, _amountDueMeta));
    } else if (isInserting) {
      context.missing(_amountDueMeta);
    }
    if (data.containsKey('amount_paid')) {
      context.handle(
          _amountPaidMeta,
          amountPaid.isAcceptableOrUnknown(
              data['amount_paid']!, _amountPaidMeta));
    } else if (isInserting) {
      context.missing(_amountPaidMeta);
    }
    if (data.containsKey('payment_method')) {
      context.handle(
          _paymentMethodMeta,
          paymentMethod.isAcceptableOrUnknown(
              data['payment_method']!, _paymentMethodMeta));
    } else if (isInserting) {
      context.missing(_paymentMethodMeta);
    }
    if (data.containsKey('status')) {
      context.handle(_statusMeta,
          status.isAcceptableOrUnknown(data['status']!, _statusMeta));
    }
    if (data.containsKey('reference_number')) {
      context.handle(
          _referenceNumberMeta,
          referenceNumber.isAcceptableOrUnknown(
              data['reference_number']!, _referenceNumberMeta));
    }
    if (data.containsKey('paid_at')) {
      context.handle(_paidAtMeta,
          paidAt.isAcceptableOrUnknown(data['paid_at']!, _paidAtMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  PaymentLocal map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return PaymentLocal(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      rowVersion: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}row_version'])!,
      isDeleted: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_deleted'])!,
      lastModifiedHlc: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}last_modified_hlc']),
      isSynced: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_synced'])!,
      orderId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}order_id'])!,
      outletId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}outlet_id'])!,
      shiftSessionId: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}shift_session_id']),
      amountDue: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}amount_due'])!,
      amountPaid: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}amount_paid'])!,
      paymentMethod: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}payment_method'])!,
      status: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}status'])!,
      referenceNumber: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}reference_number']),
      paidAt: attachedDatabase.typeMapping
          .read(DriftSqlType.dateTime, data['${effectivePrefix}paid_at']),
    );
  }

  @override
  $PaymentsTable createAlias(String alias) {
    return $PaymentsTable(attachedDatabase, alias);
  }
}

class PaymentLocal extends DataClass implements Insertable<PaymentLocal> {
  final String id;
  final int rowVersion;
  final bool isDeleted;
  final String? lastModifiedHlc;
  final bool isSynced;
  final String orderId;
  final String outletId;
  final String? shiftSessionId;
  final double amountDue;
  final double amountPaid;
  final String paymentMethod;
  final String status;
  final String? referenceNumber;
  final DateTime? paidAt;
  const PaymentLocal(
      {required this.id,
      required this.rowVersion,
      required this.isDeleted,
      this.lastModifiedHlc,
      required this.isSynced,
      required this.orderId,
      required this.outletId,
      this.shiftSessionId,
      required this.amountDue,
      required this.amountPaid,
      required this.paymentMethod,
      required this.status,
      this.referenceNumber,
      this.paidAt});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['row_version'] = Variable<int>(rowVersion);
    map['is_deleted'] = Variable<bool>(isDeleted);
    if (!nullToAbsent || lastModifiedHlc != null) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc);
    }
    map['is_synced'] = Variable<bool>(isSynced);
    map['order_id'] = Variable<String>(orderId);
    map['outlet_id'] = Variable<String>(outletId);
    if (!nullToAbsent || shiftSessionId != null) {
      map['shift_session_id'] = Variable<String>(shiftSessionId);
    }
    map['amount_due'] = Variable<double>(amountDue);
    map['amount_paid'] = Variable<double>(amountPaid);
    map['payment_method'] = Variable<String>(paymentMethod);
    map['status'] = Variable<String>(status);
    if (!nullToAbsent || referenceNumber != null) {
      map['reference_number'] = Variable<String>(referenceNumber);
    }
    if (!nullToAbsent || paidAt != null) {
      map['paid_at'] = Variable<DateTime>(paidAt);
    }
    return map;
  }

  PaymentsCompanion toCompanion(bool nullToAbsent) {
    return PaymentsCompanion(
      id: Value(id),
      rowVersion: Value(rowVersion),
      isDeleted: Value(isDeleted),
      lastModifiedHlc: lastModifiedHlc == null && nullToAbsent
          ? const Value.absent()
          : Value(lastModifiedHlc),
      isSynced: Value(isSynced),
      orderId: Value(orderId),
      outletId: Value(outletId),
      shiftSessionId: shiftSessionId == null && nullToAbsent
          ? const Value.absent()
          : Value(shiftSessionId),
      amountDue: Value(amountDue),
      amountPaid: Value(amountPaid),
      paymentMethod: Value(paymentMethod),
      status: Value(status),
      referenceNumber: referenceNumber == null && nullToAbsent
          ? const Value.absent()
          : Value(referenceNumber),
      paidAt:
          paidAt == null && nullToAbsent ? const Value.absent() : Value(paidAt),
    );
  }

  factory PaymentLocal.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return PaymentLocal(
      id: serializer.fromJson<String>(json['id']),
      rowVersion: serializer.fromJson<int>(json['rowVersion']),
      isDeleted: serializer.fromJson<bool>(json['isDeleted']),
      lastModifiedHlc: serializer.fromJson<String?>(json['lastModifiedHlc']),
      isSynced: serializer.fromJson<bool>(json['isSynced']),
      orderId: serializer.fromJson<String>(json['orderId']),
      outletId: serializer.fromJson<String>(json['outletId']),
      shiftSessionId: serializer.fromJson<String?>(json['shiftSessionId']),
      amountDue: serializer.fromJson<double>(json['amountDue']),
      amountPaid: serializer.fromJson<double>(json['amountPaid']),
      paymentMethod: serializer.fromJson<String>(json['paymentMethod']),
      status: serializer.fromJson<String>(json['status']),
      referenceNumber: serializer.fromJson<String?>(json['referenceNumber']),
      paidAt: serializer.fromJson<DateTime?>(json['paidAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'rowVersion': serializer.toJson<int>(rowVersion),
      'isDeleted': serializer.toJson<bool>(isDeleted),
      'lastModifiedHlc': serializer.toJson<String?>(lastModifiedHlc),
      'isSynced': serializer.toJson<bool>(isSynced),
      'orderId': serializer.toJson<String>(orderId),
      'outletId': serializer.toJson<String>(outletId),
      'shiftSessionId': serializer.toJson<String?>(shiftSessionId),
      'amountDue': serializer.toJson<double>(amountDue),
      'amountPaid': serializer.toJson<double>(amountPaid),
      'paymentMethod': serializer.toJson<String>(paymentMethod),
      'status': serializer.toJson<String>(status),
      'referenceNumber': serializer.toJson<String?>(referenceNumber),
      'paidAt': serializer.toJson<DateTime?>(paidAt),
    };
  }

  PaymentLocal copyWith(
          {String? id,
          int? rowVersion,
          bool? isDeleted,
          Value<String?> lastModifiedHlc = const Value.absent(),
          bool? isSynced,
          String? orderId,
          String? outletId,
          Value<String?> shiftSessionId = const Value.absent(),
          double? amountDue,
          double? amountPaid,
          String? paymentMethod,
          String? status,
          Value<String?> referenceNumber = const Value.absent(),
          Value<DateTime?> paidAt = const Value.absent()}) =>
      PaymentLocal(
        id: id ?? this.id,
        rowVersion: rowVersion ?? this.rowVersion,
        isDeleted: isDeleted ?? this.isDeleted,
        lastModifiedHlc: lastModifiedHlc.present
            ? lastModifiedHlc.value
            : this.lastModifiedHlc,
        isSynced: isSynced ?? this.isSynced,
        orderId: orderId ?? this.orderId,
        outletId: outletId ?? this.outletId,
        shiftSessionId:
            shiftSessionId.present ? shiftSessionId.value : this.shiftSessionId,
        amountDue: amountDue ?? this.amountDue,
        amountPaid: amountPaid ?? this.amountPaid,
        paymentMethod: paymentMethod ?? this.paymentMethod,
        status: status ?? this.status,
        referenceNumber: referenceNumber.present
            ? referenceNumber.value
            : this.referenceNumber,
        paidAt: paidAt.present ? paidAt.value : this.paidAt,
      );
  PaymentLocal copyWithCompanion(PaymentsCompanion data) {
    return PaymentLocal(
      id: data.id.present ? data.id.value : this.id,
      rowVersion:
          data.rowVersion.present ? data.rowVersion.value : this.rowVersion,
      isDeleted: data.isDeleted.present ? data.isDeleted.value : this.isDeleted,
      lastModifiedHlc: data.lastModifiedHlc.present
          ? data.lastModifiedHlc.value
          : this.lastModifiedHlc,
      isSynced: data.isSynced.present ? data.isSynced.value : this.isSynced,
      orderId: data.orderId.present ? data.orderId.value : this.orderId,
      outletId: data.outletId.present ? data.outletId.value : this.outletId,
      shiftSessionId: data.shiftSessionId.present
          ? data.shiftSessionId.value
          : this.shiftSessionId,
      amountDue: data.amountDue.present ? data.amountDue.value : this.amountDue,
      amountPaid:
          data.amountPaid.present ? data.amountPaid.value : this.amountPaid,
      paymentMethod: data.paymentMethod.present
          ? data.paymentMethod.value
          : this.paymentMethod,
      status: data.status.present ? data.status.value : this.status,
      referenceNumber: data.referenceNumber.present
          ? data.referenceNumber.value
          : this.referenceNumber,
      paidAt: data.paidAt.present ? data.paidAt.value : this.paidAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('PaymentLocal(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('orderId: $orderId, ')
          ..write('outletId: $outletId, ')
          ..write('shiftSessionId: $shiftSessionId, ')
          ..write('amountDue: $amountDue, ')
          ..write('amountPaid: $amountPaid, ')
          ..write('paymentMethod: $paymentMethod, ')
          ..write('status: $status, ')
          ..write('referenceNumber: $referenceNumber, ')
          ..write('paidAt: $paidAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
      id,
      rowVersion,
      isDeleted,
      lastModifiedHlc,
      isSynced,
      orderId,
      outletId,
      shiftSessionId,
      amountDue,
      amountPaid,
      paymentMethod,
      status,
      referenceNumber,
      paidAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is PaymentLocal &&
          other.id == this.id &&
          other.rowVersion == this.rowVersion &&
          other.isDeleted == this.isDeleted &&
          other.lastModifiedHlc == this.lastModifiedHlc &&
          other.isSynced == this.isSynced &&
          other.orderId == this.orderId &&
          other.outletId == this.outletId &&
          other.shiftSessionId == this.shiftSessionId &&
          other.amountDue == this.amountDue &&
          other.amountPaid == this.amountPaid &&
          other.paymentMethod == this.paymentMethod &&
          other.status == this.status &&
          other.referenceNumber == this.referenceNumber &&
          other.paidAt == this.paidAt);
}

class PaymentsCompanion extends UpdateCompanion<PaymentLocal> {
  final Value<String> id;
  final Value<int> rowVersion;
  final Value<bool> isDeleted;
  final Value<String?> lastModifiedHlc;
  final Value<bool> isSynced;
  final Value<String> orderId;
  final Value<String> outletId;
  final Value<String?> shiftSessionId;
  final Value<double> amountDue;
  final Value<double> amountPaid;
  final Value<String> paymentMethod;
  final Value<String> status;
  final Value<String?> referenceNumber;
  final Value<DateTime?> paidAt;
  final Value<int> rowid;
  const PaymentsCompanion({
    this.id = const Value.absent(),
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    this.orderId = const Value.absent(),
    this.outletId = const Value.absent(),
    this.shiftSessionId = const Value.absent(),
    this.amountDue = const Value.absent(),
    this.amountPaid = const Value.absent(),
    this.paymentMethod = const Value.absent(),
    this.status = const Value.absent(),
    this.referenceNumber = const Value.absent(),
    this.paidAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  PaymentsCompanion.insert({
    required String id,
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    required String orderId,
    required String outletId,
    this.shiftSessionId = const Value.absent(),
    required double amountDue,
    required double amountPaid,
    required String paymentMethod,
    this.status = const Value.absent(),
    this.referenceNumber = const Value.absent(),
    this.paidAt = const Value.absent(),
    this.rowid = const Value.absent(),
  })  : id = Value(id),
        orderId = Value(orderId),
        outletId = Value(outletId),
        amountDue = Value(amountDue),
        amountPaid = Value(amountPaid),
        paymentMethod = Value(paymentMethod);
  static Insertable<PaymentLocal> custom({
    Expression<String>? id,
    Expression<int>? rowVersion,
    Expression<bool>? isDeleted,
    Expression<String>? lastModifiedHlc,
    Expression<bool>? isSynced,
    Expression<String>? orderId,
    Expression<String>? outletId,
    Expression<String>? shiftSessionId,
    Expression<double>? amountDue,
    Expression<double>? amountPaid,
    Expression<String>? paymentMethod,
    Expression<String>? status,
    Expression<String>? referenceNumber,
    Expression<DateTime>? paidAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (rowVersion != null) 'row_version': rowVersion,
      if (isDeleted != null) 'is_deleted': isDeleted,
      if (lastModifiedHlc != null) 'last_modified_hlc': lastModifiedHlc,
      if (isSynced != null) 'is_synced': isSynced,
      if (orderId != null) 'order_id': orderId,
      if (outletId != null) 'outlet_id': outletId,
      if (shiftSessionId != null) 'shift_session_id': shiftSessionId,
      if (amountDue != null) 'amount_due': amountDue,
      if (amountPaid != null) 'amount_paid': amountPaid,
      if (paymentMethod != null) 'payment_method': paymentMethod,
      if (status != null) 'status': status,
      if (referenceNumber != null) 'reference_number': referenceNumber,
      if (paidAt != null) 'paid_at': paidAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  PaymentsCompanion copyWith(
      {Value<String>? id,
      Value<int>? rowVersion,
      Value<bool>? isDeleted,
      Value<String?>? lastModifiedHlc,
      Value<bool>? isSynced,
      Value<String>? orderId,
      Value<String>? outletId,
      Value<String?>? shiftSessionId,
      Value<double>? amountDue,
      Value<double>? amountPaid,
      Value<String>? paymentMethod,
      Value<String>? status,
      Value<String?>? referenceNumber,
      Value<DateTime?>? paidAt,
      Value<int>? rowid}) {
    return PaymentsCompanion(
      id: id ?? this.id,
      rowVersion: rowVersion ?? this.rowVersion,
      isDeleted: isDeleted ?? this.isDeleted,
      lastModifiedHlc: lastModifiedHlc ?? this.lastModifiedHlc,
      isSynced: isSynced ?? this.isSynced,
      orderId: orderId ?? this.orderId,
      outletId: outletId ?? this.outletId,
      shiftSessionId: shiftSessionId ?? this.shiftSessionId,
      amountDue: amountDue ?? this.amountDue,
      amountPaid: amountPaid ?? this.amountPaid,
      paymentMethod: paymentMethod ?? this.paymentMethod,
      status: status ?? this.status,
      referenceNumber: referenceNumber ?? this.referenceNumber,
      paidAt: paidAt ?? this.paidAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (rowVersion.present) {
      map['row_version'] = Variable<int>(rowVersion.value);
    }
    if (isDeleted.present) {
      map['is_deleted'] = Variable<bool>(isDeleted.value);
    }
    if (lastModifiedHlc.present) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc.value);
    }
    if (isSynced.present) {
      map['is_synced'] = Variable<bool>(isSynced.value);
    }
    if (orderId.present) {
      map['order_id'] = Variable<String>(orderId.value);
    }
    if (outletId.present) {
      map['outlet_id'] = Variable<String>(outletId.value);
    }
    if (shiftSessionId.present) {
      map['shift_session_id'] = Variable<String>(shiftSessionId.value);
    }
    if (amountDue.present) {
      map['amount_due'] = Variable<double>(amountDue.value);
    }
    if (amountPaid.present) {
      map['amount_paid'] = Variable<double>(amountPaid.value);
    }
    if (paymentMethod.present) {
      map['payment_method'] = Variable<String>(paymentMethod.value);
    }
    if (status.present) {
      map['status'] = Variable<String>(status.value);
    }
    if (referenceNumber.present) {
      map['reference_number'] = Variable<String>(referenceNumber.value);
    }
    if (paidAt.present) {
      map['paid_at'] = Variable<DateTime>(paidAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('PaymentsCompanion(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('orderId: $orderId, ')
          ..write('outletId: $outletId, ')
          ..write('shiftSessionId: $shiftSessionId, ')
          ..write('amountDue: $amountDue, ')
          ..write('amountPaid: $amountPaid, ')
          ..write('paymentMethod: $paymentMethod, ')
          ..write('status: $status, ')
          ..write('referenceNumber: $referenceNumber, ')
          ..write('paidAt: $paidAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $ShiftsTable extends Shifts with TableInfo<$ShiftsTable, ShiftLocal> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $ShiftsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
      'id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _rowVersionMeta =
      const VerificationMeta('rowVersion');
  @override
  late final GeneratedColumn<int> rowVersion = GeneratedColumn<int>(
      'row_version', aliasedName, false,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultValue: const Constant(0));
  static const VerificationMeta _isDeletedMeta =
      const VerificationMeta('isDeleted');
  @override
  late final GeneratedColumn<bool> isDeleted = GeneratedColumn<bool>(
      'is_deleted', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_deleted" IN (0, 1))'),
      defaultValue: const Constant(false));
  static const VerificationMeta _lastModifiedHlcMeta =
      const VerificationMeta('lastModifiedHlc');
  @override
  late final GeneratedColumn<String> lastModifiedHlc = GeneratedColumn<String>(
      'last_modified_hlc', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _isSyncedMeta =
      const VerificationMeta('isSynced');
  @override
  late final GeneratedColumn<bool> isSynced = GeneratedColumn<bool>(
      'is_synced', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_synced" IN (0, 1))'),
      defaultValue: const Constant(true));
  static const VerificationMeta _outletIdMeta =
      const VerificationMeta('outletId');
  @override
  late final GeneratedColumn<String> outletId = GeneratedColumn<String>(
      'outlet_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _userIdMeta = const VerificationMeta('userId');
  @override
  late final GeneratedColumn<String> userId = GeneratedColumn<String>(
      'user_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _statusMeta = const VerificationMeta('status');
  @override
  late final GeneratedColumn<String> status = GeneratedColumn<String>(
      'status', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('open'));
  static const VerificationMeta _startTimeMeta =
      const VerificationMeta('startTime');
  @override
  late final GeneratedColumn<DateTime> startTime = GeneratedColumn<DateTime>(
      'start_time', aliasedName, false,
      type: DriftSqlType.dateTime, requiredDuringInsert: true);
  static const VerificationMeta _endTimeMeta =
      const VerificationMeta('endTime');
  @override
  late final GeneratedColumn<DateTime> endTime = GeneratedColumn<DateTime>(
      'end_time', aliasedName, true,
      type: DriftSqlType.dateTime, requiredDuringInsert: false);
  static const VerificationMeta _startingCashMeta =
      const VerificationMeta('startingCash');
  @override
  late final GeneratedColumn<double> startingCash = GeneratedColumn<double>(
      'starting_cash', aliasedName, false,
      type: DriftSqlType.double,
      requiredDuringInsert: false,
      defaultValue: const Constant(0.0));
  static const VerificationMeta _endingCashMeta =
      const VerificationMeta('endingCash');
  @override
  late final GeneratedColumn<double> endingCash = GeneratedColumn<double>(
      'ending_cash', aliasedName, true,
      type: DriftSqlType.double, requiredDuringInsert: false);
  static const VerificationMeta _expectedEndingCashMeta =
      const VerificationMeta('expectedEndingCash');
  @override
  late final GeneratedColumn<double> expectedEndingCash =
      GeneratedColumn<double>('expected_ending_cash', aliasedName, true,
          type: DriftSqlType.double, requiredDuringInsert: false);
  static const VerificationMeta _notesMeta = const VerificationMeta('notes');
  @override
  late final GeneratedColumn<String> notes = GeneratedColumn<String>(
      'notes', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  @override
  List<GeneratedColumn> get $columns => [
        id,
        rowVersion,
        isDeleted,
        lastModifiedHlc,
        isSynced,
        outletId,
        userId,
        status,
        startTime,
        endTime,
        startingCash,
        endingCash,
        expectedEndingCash,
        notes
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'shifts';
  @override
  VerificationContext validateIntegrity(Insertable<ShiftLocal> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('row_version')) {
      context.handle(
          _rowVersionMeta,
          rowVersion.isAcceptableOrUnknown(
              data['row_version']!, _rowVersionMeta));
    }
    if (data.containsKey('is_deleted')) {
      context.handle(_isDeletedMeta,
          isDeleted.isAcceptableOrUnknown(data['is_deleted']!, _isDeletedMeta));
    }
    if (data.containsKey('last_modified_hlc')) {
      context.handle(
          _lastModifiedHlcMeta,
          lastModifiedHlc.isAcceptableOrUnknown(
              data['last_modified_hlc']!, _lastModifiedHlcMeta));
    }
    if (data.containsKey('is_synced')) {
      context.handle(_isSyncedMeta,
          isSynced.isAcceptableOrUnknown(data['is_synced']!, _isSyncedMeta));
    }
    if (data.containsKey('outlet_id')) {
      context.handle(_outletIdMeta,
          outletId.isAcceptableOrUnknown(data['outlet_id']!, _outletIdMeta));
    } else if (isInserting) {
      context.missing(_outletIdMeta);
    }
    if (data.containsKey('user_id')) {
      context.handle(_userIdMeta,
          userId.isAcceptableOrUnknown(data['user_id']!, _userIdMeta));
    } else if (isInserting) {
      context.missing(_userIdMeta);
    }
    if (data.containsKey('status')) {
      context.handle(_statusMeta,
          status.isAcceptableOrUnknown(data['status']!, _statusMeta));
    }
    if (data.containsKey('start_time')) {
      context.handle(_startTimeMeta,
          startTime.isAcceptableOrUnknown(data['start_time']!, _startTimeMeta));
    } else if (isInserting) {
      context.missing(_startTimeMeta);
    }
    if (data.containsKey('end_time')) {
      context.handle(_endTimeMeta,
          endTime.isAcceptableOrUnknown(data['end_time']!, _endTimeMeta));
    }
    if (data.containsKey('starting_cash')) {
      context.handle(
          _startingCashMeta,
          startingCash.isAcceptableOrUnknown(
              data['starting_cash']!, _startingCashMeta));
    }
    if (data.containsKey('ending_cash')) {
      context.handle(
          _endingCashMeta,
          endingCash.isAcceptableOrUnknown(
              data['ending_cash']!, _endingCashMeta));
    }
    if (data.containsKey('expected_ending_cash')) {
      context.handle(
          _expectedEndingCashMeta,
          expectedEndingCash.isAcceptableOrUnknown(
              data['expected_ending_cash']!, _expectedEndingCashMeta));
    }
    if (data.containsKey('notes')) {
      context.handle(
          _notesMeta, notes.isAcceptableOrUnknown(data['notes']!, _notesMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  ShiftLocal map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return ShiftLocal(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      rowVersion: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}row_version'])!,
      isDeleted: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_deleted'])!,
      lastModifiedHlc: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}last_modified_hlc']),
      isSynced: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_synced'])!,
      outletId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}outlet_id'])!,
      userId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}user_id'])!,
      status: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}status'])!,
      startTime: attachedDatabase.typeMapping
          .read(DriftSqlType.dateTime, data['${effectivePrefix}start_time'])!,
      endTime: attachedDatabase.typeMapping
          .read(DriftSqlType.dateTime, data['${effectivePrefix}end_time']),
      startingCash: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}starting_cash'])!,
      endingCash: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}ending_cash']),
      expectedEndingCash: attachedDatabase.typeMapping.read(
          DriftSqlType.double, data['${effectivePrefix}expected_ending_cash']),
      notes: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}notes']),
    );
  }

  @override
  $ShiftsTable createAlias(String alias) {
    return $ShiftsTable(attachedDatabase, alias);
  }
}

class ShiftLocal extends DataClass implements Insertable<ShiftLocal> {
  final String id;
  final int rowVersion;
  final bool isDeleted;
  final String? lastModifiedHlc;
  final bool isSynced;
  final String outletId;
  final String userId;
  final String status;
  final DateTime startTime;
  final DateTime? endTime;
  final double startingCash;
  final double? endingCash;
  final double? expectedEndingCash;
  final String? notes;
  const ShiftLocal(
      {required this.id,
      required this.rowVersion,
      required this.isDeleted,
      this.lastModifiedHlc,
      required this.isSynced,
      required this.outletId,
      required this.userId,
      required this.status,
      required this.startTime,
      this.endTime,
      required this.startingCash,
      this.endingCash,
      this.expectedEndingCash,
      this.notes});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['row_version'] = Variable<int>(rowVersion);
    map['is_deleted'] = Variable<bool>(isDeleted);
    if (!nullToAbsent || lastModifiedHlc != null) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc);
    }
    map['is_synced'] = Variable<bool>(isSynced);
    map['outlet_id'] = Variable<String>(outletId);
    map['user_id'] = Variable<String>(userId);
    map['status'] = Variable<String>(status);
    map['start_time'] = Variable<DateTime>(startTime);
    if (!nullToAbsent || endTime != null) {
      map['end_time'] = Variable<DateTime>(endTime);
    }
    map['starting_cash'] = Variable<double>(startingCash);
    if (!nullToAbsent || endingCash != null) {
      map['ending_cash'] = Variable<double>(endingCash);
    }
    if (!nullToAbsent || expectedEndingCash != null) {
      map['expected_ending_cash'] = Variable<double>(expectedEndingCash);
    }
    if (!nullToAbsent || notes != null) {
      map['notes'] = Variable<String>(notes);
    }
    return map;
  }

  ShiftsCompanion toCompanion(bool nullToAbsent) {
    return ShiftsCompanion(
      id: Value(id),
      rowVersion: Value(rowVersion),
      isDeleted: Value(isDeleted),
      lastModifiedHlc: lastModifiedHlc == null && nullToAbsent
          ? const Value.absent()
          : Value(lastModifiedHlc),
      isSynced: Value(isSynced),
      outletId: Value(outletId),
      userId: Value(userId),
      status: Value(status),
      startTime: Value(startTime),
      endTime: endTime == null && nullToAbsent
          ? const Value.absent()
          : Value(endTime),
      startingCash: Value(startingCash),
      endingCash: endingCash == null && nullToAbsent
          ? const Value.absent()
          : Value(endingCash),
      expectedEndingCash: expectedEndingCash == null && nullToAbsent
          ? const Value.absent()
          : Value(expectedEndingCash),
      notes:
          notes == null && nullToAbsent ? const Value.absent() : Value(notes),
    );
  }

  factory ShiftLocal.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return ShiftLocal(
      id: serializer.fromJson<String>(json['id']),
      rowVersion: serializer.fromJson<int>(json['rowVersion']),
      isDeleted: serializer.fromJson<bool>(json['isDeleted']),
      lastModifiedHlc: serializer.fromJson<String?>(json['lastModifiedHlc']),
      isSynced: serializer.fromJson<bool>(json['isSynced']),
      outletId: serializer.fromJson<String>(json['outletId']),
      userId: serializer.fromJson<String>(json['userId']),
      status: serializer.fromJson<String>(json['status']),
      startTime: serializer.fromJson<DateTime>(json['startTime']),
      endTime: serializer.fromJson<DateTime?>(json['endTime']),
      startingCash: serializer.fromJson<double>(json['startingCash']),
      endingCash: serializer.fromJson<double?>(json['endingCash']),
      expectedEndingCash:
          serializer.fromJson<double?>(json['expectedEndingCash']),
      notes: serializer.fromJson<String?>(json['notes']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'rowVersion': serializer.toJson<int>(rowVersion),
      'isDeleted': serializer.toJson<bool>(isDeleted),
      'lastModifiedHlc': serializer.toJson<String?>(lastModifiedHlc),
      'isSynced': serializer.toJson<bool>(isSynced),
      'outletId': serializer.toJson<String>(outletId),
      'userId': serializer.toJson<String>(userId),
      'status': serializer.toJson<String>(status),
      'startTime': serializer.toJson<DateTime>(startTime),
      'endTime': serializer.toJson<DateTime?>(endTime),
      'startingCash': serializer.toJson<double>(startingCash),
      'endingCash': serializer.toJson<double?>(endingCash),
      'expectedEndingCash': serializer.toJson<double?>(expectedEndingCash),
      'notes': serializer.toJson<String?>(notes),
    };
  }

  ShiftLocal copyWith(
          {String? id,
          int? rowVersion,
          bool? isDeleted,
          Value<String?> lastModifiedHlc = const Value.absent(),
          bool? isSynced,
          String? outletId,
          String? userId,
          String? status,
          DateTime? startTime,
          Value<DateTime?> endTime = const Value.absent(),
          double? startingCash,
          Value<double?> endingCash = const Value.absent(),
          Value<double?> expectedEndingCash = const Value.absent(),
          Value<String?> notes = const Value.absent()}) =>
      ShiftLocal(
        id: id ?? this.id,
        rowVersion: rowVersion ?? this.rowVersion,
        isDeleted: isDeleted ?? this.isDeleted,
        lastModifiedHlc: lastModifiedHlc.present
            ? lastModifiedHlc.value
            : this.lastModifiedHlc,
        isSynced: isSynced ?? this.isSynced,
        outletId: outletId ?? this.outletId,
        userId: userId ?? this.userId,
        status: status ?? this.status,
        startTime: startTime ?? this.startTime,
        endTime: endTime.present ? endTime.value : this.endTime,
        startingCash: startingCash ?? this.startingCash,
        endingCash: endingCash.present ? endingCash.value : this.endingCash,
        expectedEndingCash: expectedEndingCash.present
            ? expectedEndingCash.value
            : this.expectedEndingCash,
        notes: notes.present ? notes.value : this.notes,
      );
  ShiftLocal copyWithCompanion(ShiftsCompanion data) {
    return ShiftLocal(
      id: data.id.present ? data.id.value : this.id,
      rowVersion:
          data.rowVersion.present ? data.rowVersion.value : this.rowVersion,
      isDeleted: data.isDeleted.present ? data.isDeleted.value : this.isDeleted,
      lastModifiedHlc: data.lastModifiedHlc.present
          ? data.lastModifiedHlc.value
          : this.lastModifiedHlc,
      isSynced: data.isSynced.present ? data.isSynced.value : this.isSynced,
      outletId: data.outletId.present ? data.outletId.value : this.outletId,
      userId: data.userId.present ? data.userId.value : this.userId,
      status: data.status.present ? data.status.value : this.status,
      startTime: data.startTime.present ? data.startTime.value : this.startTime,
      endTime: data.endTime.present ? data.endTime.value : this.endTime,
      startingCash: data.startingCash.present
          ? data.startingCash.value
          : this.startingCash,
      endingCash:
          data.endingCash.present ? data.endingCash.value : this.endingCash,
      expectedEndingCash: data.expectedEndingCash.present
          ? data.expectedEndingCash.value
          : this.expectedEndingCash,
      notes: data.notes.present ? data.notes.value : this.notes,
    );
  }

  @override
  String toString() {
    return (StringBuffer('ShiftLocal(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('outletId: $outletId, ')
          ..write('userId: $userId, ')
          ..write('status: $status, ')
          ..write('startTime: $startTime, ')
          ..write('endTime: $endTime, ')
          ..write('startingCash: $startingCash, ')
          ..write('endingCash: $endingCash, ')
          ..write('expectedEndingCash: $expectedEndingCash, ')
          ..write('notes: $notes')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
      id,
      rowVersion,
      isDeleted,
      lastModifiedHlc,
      isSynced,
      outletId,
      userId,
      status,
      startTime,
      endTime,
      startingCash,
      endingCash,
      expectedEndingCash,
      notes);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is ShiftLocal &&
          other.id == this.id &&
          other.rowVersion == this.rowVersion &&
          other.isDeleted == this.isDeleted &&
          other.lastModifiedHlc == this.lastModifiedHlc &&
          other.isSynced == this.isSynced &&
          other.outletId == this.outletId &&
          other.userId == this.userId &&
          other.status == this.status &&
          other.startTime == this.startTime &&
          other.endTime == this.endTime &&
          other.startingCash == this.startingCash &&
          other.endingCash == this.endingCash &&
          other.expectedEndingCash == this.expectedEndingCash &&
          other.notes == this.notes);
}

class ShiftsCompanion extends UpdateCompanion<ShiftLocal> {
  final Value<String> id;
  final Value<int> rowVersion;
  final Value<bool> isDeleted;
  final Value<String?> lastModifiedHlc;
  final Value<bool> isSynced;
  final Value<String> outletId;
  final Value<String> userId;
  final Value<String> status;
  final Value<DateTime> startTime;
  final Value<DateTime?> endTime;
  final Value<double> startingCash;
  final Value<double?> endingCash;
  final Value<double?> expectedEndingCash;
  final Value<String?> notes;
  final Value<int> rowid;
  const ShiftsCompanion({
    this.id = const Value.absent(),
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    this.outletId = const Value.absent(),
    this.userId = const Value.absent(),
    this.status = const Value.absent(),
    this.startTime = const Value.absent(),
    this.endTime = const Value.absent(),
    this.startingCash = const Value.absent(),
    this.endingCash = const Value.absent(),
    this.expectedEndingCash = const Value.absent(),
    this.notes = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  ShiftsCompanion.insert({
    required String id,
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    required String outletId,
    required String userId,
    this.status = const Value.absent(),
    required DateTime startTime,
    this.endTime = const Value.absent(),
    this.startingCash = const Value.absent(),
    this.endingCash = const Value.absent(),
    this.expectedEndingCash = const Value.absent(),
    this.notes = const Value.absent(),
    this.rowid = const Value.absent(),
  })  : id = Value(id),
        outletId = Value(outletId),
        userId = Value(userId),
        startTime = Value(startTime);
  static Insertable<ShiftLocal> custom({
    Expression<String>? id,
    Expression<int>? rowVersion,
    Expression<bool>? isDeleted,
    Expression<String>? lastModifiedHlc,
    Expression<bool>? isSynced,
    Expression<String>? outletId,
    Expression<String>? userId,
    Expression<String>? status,
    Expression<DateTime>? startTime,
    Expression<DateTime>? endTime,
    Expression<double>? startingCash,
    Expression<double>? endingCash,
    Expression<double>? expectedEndingCash,
    Expression<String>? notes,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (rowVersion != null) 'row_version': rowVersion,
      if (isDeleted != null) 'is_deleted': isDeleted,
      if (lastModifiedHlc != null) 'last_modified_hlc': lastModifiedHlc,
      if (isSynced != null) 'is_synced': isSynced,
      if (outletId != null) 'outlet_id': outletId,
      if (userId != null) 'user_id': userId,
      if (status != null) 'status': status,
      if (startTime != null) 'start_time': startTime,
      if (endTime != null) 'end_time': endTime,
      if (startingCash != null) 'starting_cash': startingCash,
      if (endingCash != null) 'ending_cash': endingCash,
      if (expectedEndingCash != null)
        'expected_ending_cash': expectedEndingCash,
      if (notes != null) 'notes': notes,
      if (rowid != null) 'rowid': rowid,
    });
  }

  ShiftsCompanion copyWith(
      {Value<String>? id,
      Value<int>? rowVersion,
      Value<bool>? isDeleted,
      Value<String?>? lastModifiedHlc,
      Value<bool>? isSynced,
      Value<String>? outletId,
      Value<String>? userId,
      Value<String>? status,
      Value<DateTime>? startTime,
      Value<DateTime?>? endTime,
      Value<double>? startingCash,
      Value<double?>? endingCash,
      Value<double?>? expectedEndingCash,
      Value<String?>? notes,
      Value<int>? rowid}) {
    return ShiftsCompanion(
      id: id ?? this.id,
      rowVersion: rowVersion ?? this.rowVersion,
      isDeleted: isDeleted ?? this.isDeleted,
      lastModifiedHlc: lastModifiedHlc ?? this.lastModifiedHlc,
      isSynced: isSynced ?? this.isSynced,
      outletId: outletId ?? this.outletId,
      userId: userId ?? this.userId,
      status: status ?? this.status,
      startTime: startTime ?? this.startTime,
      endTime: endTime ?? this.endTime,
      startingCash: startingCash ?? this.startingCash,
      endingCash: endingCash ?? this.endingCash,
      expectedEndingCash: expectedEndingCash ?? this.expectedEndingCash,
      notes: notes ?? this.notes,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (rowVersion.present) {
      map['row_version'] = Variable<int>(rowVersion.value);
    }
    if (isDeleted.present) {
      map['is_deleted'] = Variable<bool>(isDeleted.value);
    }
    if (lastModifiedHlc.present) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc.value);
    }
    if (isSynced.present) {
      map['is_synced'] = Variable<bool>(isSynced.value);
    }
    if (outletId.present) {
      map['outlet_id'] = Variable<String>(outletId.value);
    }
    if (userId.present) {
      map['user_id'] = Variable<String>(userId.value);
    }
    if (status.present) {
      map['status'] = Variable<String>(status.value);
    }
    if (startTime.present) {
      map['start_time'] = Variable<DateTime>(startTime.value);
    }
    if (endTime.present) {
      map['end_time'] = Variable<DateTime>(endTime.value);
    }
    if (startingCash.present) {
      map['starting_cash'] = Variable<double>(startingCash.value);
    }
    if (endingCash.present) {
      map['ending_cash'] = Variable<double>(endingCash.value);
    }
    if (expectedEndingCash.present) {
      map['expected_ending_cash'] = Variable<double>(expectedEndingCash.value);
    }
    if (notes.present) {
      map['notes'] = Variable<String>(notes.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('ShiftsCompanion(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('outletId: $outletId, ')
          ..write('userId: $userId, ')
          ..write('status: $status, ')
          ..write('startTime: $startTime, ')
          ..write('endTime: $endTime, ')
          ..write('startingCash: $startingCash, ')
          ..write('endingCash: $endingCash, ')
          ..write('expectedEndingCash: $expectedEndingCash, ')
          ..write('notes: $notes, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $CashActivitiesTable extends CashActivities
    with TableInfo<$CashActivitiesTable, CashActivityLocal> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $CashActivitiesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
      'id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _rowVersionMeta =
      const VerificationMeta('rowVersion');
  @override
  late final GeneratedColumn<int> rowVersion = GeneratedColumn<int>(
      'row_version', aliasedName, false,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultValue: const Constant(0));
  static const VerificationMeta _isDeletedMeta =
      const VerificationMeta('isDeleted');
  @override
  late final GeneratedColumn<bool> isDeleted = GeneratedColumn<bool>(
      'is_deleted', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_deleted" IN (0, 1))'),
      defaultValue: const Constant(false));
  static const VerificationMeta _lastModifiedHlcMeta =
      const VerificationMeta('lastModifiedHlc');
  @override
  late final GeneratedColumn<String> lastModifiedHlc = GeneratedColumn<String>(
      'last_modified_hlc', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _isSyncedMeta =
      const VerificationMeta('isSynced');
  @override
  late final GeneratedColumn<bool> isSynced = GeneratedColumn<bool>(
      'is_synced', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_synced" IN (0, 1))'),
      defaultValue: const Constant(true));
  static const VerificationMeta _shiftIdMeta =
      const VerificationMeta('shiftId');
  @override
  late final GeneratedColumn<String> shiftId = GeneratedColumn<String>(
      'shift_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _activityTypeMeta =
      const VerificationMeta('activityType');
  @override
  late final GeneratedColumn<String> activityType = GeneratedColumn<String>(
      'activity_type', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _amountMeta = const VerificationMeta('amount');
  @override
  late final GeneratedColumn<double> amount = GeneratedColumn<double>(
      'amount', aliasedName, false,
      type: DriftSqlType.double, requiredDuringInsert: true);
  static const VerificationMeta _descriptionMeta =
      const VerificationMeta('description');
  @override
  late final GeneratedColumn<String> description = GeneratedColumn<String>(
      'description', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  @override
  List<GeneratedColumn> get $columns => [
        id,
        rowVersion,
        isDeleted,
        lastModifiedHlc,
        isSynced,
        shiftId,
        activityType,
        amount,
        description
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'cash_activities';
  @override
  VerificationContext validateIntegrity(Insertable<CashActivityLocal> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('row_version')) {
      context.handle(
          _rowVersionMeta,
          rowVersion.isAcceptableOrUnknown(
              data['row_version']!, _rowVersionMeta));
    }
    if (data.containsKey('is_deleted')) {
      context.handle(_isDeletedMeta,
          isDeleted.isAcceptableOrUnknown(data['is_deleted']!, _isDeletedMeta));
    }
    if (data.containsKey('last_modified_hlc')) {
      context.handle(
          _lastModifiedHlcMeta,
          lastModifiedHlc.isAcceptableOrUnknown(
              data['last_modified_hlc']!, _lastModifiedHlcMeta));
    }
    if (data.containsKey('is_synced')) {
      context.handle(_isSyncedMeta,
          isSynced.isAcceptableOrUnknown(data['is_synced']!, _isSyncedMeta));
    }
    if (data.containsKey('shift_id')) {
      context.handle(_shiftIdMeta,
          shiftId.isAcceptableOrUnknown(data['shift_id']!, _shiftIdMeta));
    } else if (isInserting) {
      context.missing(_shiftIdMeta);
    }
    if (data.containsKey('activity_type')) {
      context.handle(
          _activityTypeMeta,
          activityType.isAcceptableOrUnknown(
              data['activity_type']!, _activityTypeMeta));
    } else if (isInserting) {
      context.missing(_activityTypeMeta);
    }
    if (data.containsKey('amount')) {
      context.handle(_amountMeta,
          amount.isAcceptableOrUnknown(data['amount']!, _amountMeta));
    } else if (isInserting) {
      context.missing(_amountMeta);
    }
    if (data.containsKey('description')) {
      context.handle(
          _descriptionMeta,
          description.isAcceptableOrUnknown(
              data['description']!, _descriptionMeta));
    } else if (isInserting) {
      context.missing(_descriptionMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  CashActivityLocal map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return CashActivityLocal(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      rowVersion: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}row_version'])!,
      isDeleted: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_deleted'])!,
      lastModifiedHlc: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}last_modified_hlc']),
      isSynced: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_synced'])!,
      shiftId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}shift_id'])!,
      activityType: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}activity_type'])!,
      amount: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}amount'])!,
      description: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}description'])!,
    );
  }

  @override
  $CashActivitiesTable createAlias(String alias) {
    return $CashActivitiesTable(attachedDatabase, alias);
  }
}

class CashActivityLocal extends DataClass
    implements Insertable<CashActivityLocal> {
  final String id;
  final int rowVersion;
  final bool isDeleted;
  final String? lastModifiedHlc;
  final bool isSynced;
  final String shiftId;
  final String activityType;
  final double amount;
  final String description;
  const CashActivityLocal(
      {required this.id,
      required this.rowVersion,
      required this.isDeleted,
      this.lastModifiedHlc,
      required this.isSynced,
      required this.shiftId,
      required this.activityType,
      required this.amount,
      required this.description});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['row_version'] = Variable<int>(rowVersion);
    map['is_deleted'] = Variable<bool>(isDeleted);
    if (!nullToAbsent || lastModifiedHlc != null) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc);
    }
    map['is_synced'] = Variable<bool>(isSynced);
    map['shift_id'] = Variable<String>(shiftId);
    map['activity_type'] = Variable<String>(activityType);
    map['amount'] = Variable<double>(amount);
    map['description'] = Variable<String>(description);
    return map;
  }

  CashActivitiesCompanion toCompanion(bool nullToAbsent) {
    return CashActivitiesCompanion(
      id: Value(id),
      rowVersion: Value(rowVersion),
      isDeleted: Value(isDeleted),
      lastModifiedHlc: lastModifiedHlc == null && nullToAbsent
          ? const Value.absent()
          : Value(lastModifiedHlc),
      isSynced: Value(isSynced),
      shiftId: Value(shiftId),
      activityType: Value(activityType),
      amount: Value(amount),
      description: Value(description),
    );
  }

  factory CashActivityLocal.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return CashActivityLocal(
      id: serializer.fromJson<String>(json['id']),
      rowVersion: serializer.fromJson<int>(json['rowVersion']),
      isDeleted: serializer.fromJson<bool>(json['isDeleted']),
      lastModifiedHlc: serializer.fromJson<String?>(json['lastModifiedHlc']),
      isSynced: serializer.fromJson<bool>(json['isSynced']),
      shiftId: serializer.fromJson<String>(json['shiftId']),
      activityType: serializer.fromJson<String>(json['activityType']),
      amount: serializer.fromJson<double>(json['amount']),
      description: serializer.fromJson<String>(json['description']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'rowVersion': serializer.toJson<int>(rowVersion),
      'isDeleted': serializer.toJson<bool>(isDeleted),
      'lastModifiedHlc': serializer.toJson<String?>(lastModifiedHlc),
      'isSynced': serializer.toJson<bool>(isSynced),
      'shiftId': serializer.toJson<String>(shiftId),
      'activityType': serializer.toJson<String>(activityType),
      'amount': serializer.toJson<double>(amount),
      'description': serializer.toJson<String>(description),
    };
  }

  CashActivityLocal copyWith(
          {String? id,
          int? rowVersion,
          bool? isDeleted,
          Value<String?> lastModifiedHlc = const Value.absent(),
          bool? isSynced,
          String? shiftId,
          String? activityType,
          double? amount,
          String? description}) =>
      CashActivityLocal(
        id: id ?? this.id,
        rowVersion: rowVersion ?? this.rowVersion,
        isDeleted: isDeleted ?? this.isDeleted,
        lastModifiedHlc: lastModifiedHlc.present
            ? lastModifiedHlc.value
            : this.lastModifiedHlc,
        isSynced: isSynced ?? this.isSynced,
        shiftId: shiftId ?? this.shiftId,
        activityType: activityType ?? this.activityType,
        amount: amount ?? this.amount,
        description: description ?? this.description,
      );
  CashActivityLocal copyWithCompanion(CashActivitiesCompanion data) {
    return CashActivityLocal(
      id: data.id.present ? data.id.value : this.id,
      rowVersion:
          data.rowVersion.present ? data.rowVersion.value : this.rowVersion,
      isDeleted: data.isDeleted.present ? data.isDeleted.value : this.isDeleted,
      lastModifiedHlc: data.lastModifiedHlc.present
          ? data.lastModifiedHlc.value
          : this.lastModifiedHlc,
      isSynced: data.isSynced.present ? data.isSynced.value : this.isSynced,
      shiftId: data.shiftId.present ? data.shiftId.value : this.shiftId,
      activityType: data.activityType.present
          ? data.activityType.value
          : this.activityType,
      amount: data.amount.present ? data.amount.value : this.amount,
      description:
          data.description.present ? data.description.value : this.description,
    );
  }

  @override
  String toString() {
    return (StringBuffer('CashActivityLocal(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('shiftId: $shiftId, ')
          ..write('activityType: $activityType, ')
          ..write('amount: $amount, ')
          ..write('description: $description')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, rowVersion, isDeleted, lastModifiedHlc,
      isSynced, shiftId, activityType, amount, description);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is CashActivityLocal &&
          other.id == this.id &&
          other.rowVersion == this.rowVersion &&
          other.isDeleted == this.isDeleted &&
          other.lastModifiedHlc == this.lastModifiedHlc &&
          other.isSynced == this.isSynced &&
          other.shiftId == this.shiftId &&
          other.activityType == this.activityType &&
          other.amount == this.amount &&
          other.description == this.description);
}

class CashActivitiesCompanion extends UpdateCompanion<CashActivityLocal> {
  final Value<String> id;
  final Value<int> rowVersion;
  final Value<bool> isDeleted;
  final Value<String?> lastModifiedHlc;
  final Value<bool> isSynced;
  final Value<String> shiftId;
  final Value<String> activityType;
  final Value<double> amount;
  final Value<String> description;
  final Value<int> rowid;
  const CashActivitiesCompanion({
    this.id = const Value.absent(),
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    this.shiftId = const Value.absent(),
    this.activityType = const Value.absent(),
    this.amount = const Value.absent(),
    this.description = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  CashActivitiesCompanion.insert({
    required String id,
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    required String shiftId,
    required String activityType,
    required double amount,
    required String description,
    this.rowid = const Value.absent(),
  })  : id = Value(id),
        shiftId = Value(shiftId),
        activityType = Value(activityType),
        amount = Value(amount),
        description = Value(description);
  static Insertable<CashActivityLocal> custom({
    Expression<String>? id,
    Expression<int>? rowVersion,
    Expression<bool>? isDeleted,
    Expression<String>? lastModifiedHlc,
    Expression<bool>? isSynced,
    Expression<String>? shiftId,
    Expression<String>? activityType,
    Expression<double>? amount,
    Expression<String>? description,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (rowVersion != null) 'row_version': rowVersion,
      if (isDeleted != null) 'is_deleted': isDeleted,
      if (lastModifiedHlc != null) 'last_modified_hlc': lastModifiedHlc,
      if (isSynced != null) 'is_synced': isSynced,
      if (shiftId != null) 'shift_id': shiftId,
      if (activityType != null) 'activity_type': activityType,
      if (amount != null) 'amount': amount,
      if (description != null) 'description': description,
      if (rowid != null) 'rowid': rowid,
    });
  }

  CashActivitiesCompanion copyWith(
      {Value<String>? id,
      Value<int>? rowVersion,
      Value<bool>? isDeleted,
      Value<String?>? lastModifiedHlc,
      Value<bool>? isSynced,
      Value<String>? shiftId,
      Value<String>? activityType,
      Value<double>? amount,
      Value<String>? description,
      Value<int>? rowid}) {
    return CashActivitiesCompanion(
      id: id ?? this.id,
      rowVersion: rowVersion ?? this.rowVersion,
      isDeleted: isDeleted ?? this.isDeleted,
      lastModifiedHlc: lastModifiedHlc ?? this.lastModifiedHlc,
      isSynced: isSynced ?? this.isSynced,
      shiftId: shiftId ?? this.shiftId,
      activityType: activityType ?? this.activityType,
      amount: amount ?? this.amount,
      description: description ?? this.description,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (rowVersion.present) {
      map['row_version'] = Variable<int>(rowVersion.value);
    }
    if (isDeleted.present) {
      map['is_deleted'] = Variable<bool>(isDeleted.value);
    }
    if (lastModifiedHlc.present) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc.value);
    }
    if (isSynced.present) {
      map['is_synced'] = Variable<bool>(isSynced.value);
    }
    if (shiftId.present) {
      map['shift_id'] = Variable<String>(shiftId.value);
    }
    if (activityType.present) {
      map['activity_type'] = Variable<String>(activityType.value);
    }
    if (amount.present) {
      map['amount'] = Variable<double>(amount.value);
    }
    if (description.present) {
      map['description'] = Variable<String>(description.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('CashActivitiesCompanion(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('shiftId: $shiftId, ')
          ..write('activityType: $activityType, ')
          ..write('amount: $amount, ')
          ..write('description: $description, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $IngredientsTable extends Ingredients
    with TableInfo<$IngredientsTable, IngredientLocal> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $IngredientsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
      'id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _rowVersionMeta =
      const VerificationMeta('rowVersion');
  @override
  late final GeneratedColumn<int> rowVersion = GeneratedColumn<int>(
      'row_version', aliasedName, false,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultValue: const Constant(0));
  static const VerificationMeta _isDeletedMeta =
      const VerificationMeta('isDeleted');
  @override
  late final GeneratedColumn<bool> isDeleted = GeneratedColumn<bool>(
      'is_deleted', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_deleted" IN (0, 1))'),
      defaultValue: const Constant(false));
  static const VerificationMeta _lastModifiedHlcMeta =
      const VerificationMeta('lastModifiedHlc');
  @override
  late final GeneratedColumn<String> lastModifiedHlc = GeneratedColumn<String>(
      'last_modified_hlc', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _isSyncedMeta =
      const VerificationMeta('isSynced');
  @override
  late final GeneratedColumn<bool> isSynced = GeneratedColumn<bool>(
      'is_synced', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_synced" IN (0, 1))'),
      defaultValue: const Constant(true));
  static const VerificationMeta _brandIdMeta =
      const VerificationMeta('brandId');
  @override
  late final GeneratedColumn<String> brandId = GeneratedColumn<String>(
      'brand_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _nameMeta = const VerificationMeta('name');
  @override
  late final GeneratedColumn<String> name = GeneratedColumn<String>(
      'name', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _trackingModeMeta =
      const VerificationMeta('trackingMode');
  @override
  late final GeneratedColumn<String> trackingMode = GeneratedColumn<String>(
      'tracking_mode', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _baseUnitMeta =
      const VerificationMeta('baseUnit');
  @override
  late final GeneratedColumn<String> baseUnit = GeneratedColumn<String>(
      'base_unit', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _unitTypeMeta =
      const VerificationMeta('unitType');
  @override
  late final GeneratedColumn<String> unitType = GeneratedColumn<String>(
      'unit_type', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _buyPriceMeta =
      const VerificationMeta('buyPrice');
  @override
  late final GeneratedColumn<double> buyPrice = GeneratedColumn<double>(
      'buy_price', aliasedName, false,
      type: DriftSqlType.double,
      requiredDuringInsert: false,
      defaultValue: const Constant(0.0));
  static const VerificationMeta _buyQtyMeta = const VerificationMeta('buyQty');
  @override
  late final GeneratedColumn<double> buyQty = GeneratedColumn<double>(
      'buy_qty', aliasedName, false,
      type: DriftSqlType.double,
      requiredDuringInsert: false,
      defaultValue: const Constant(1.0));
  static const VerificationMeta _costPerBaseUnitMeta =
      const VerificationMeta('costPerBaseUnit');
  @override
  late final GeneratedColumn<double> costPerBaseUnit = GeneratedColumn<double>(
      'cost_per_base_unit', aliasedName, false,
      type: DriftSqlType.double,
      requiredDuringInsert: false,
      defaultValue: const Constant(0.0));
  static const VerificationMeta _ingredientTypeMeta =
      const VerificationMeta('ingredientType');
  @override
  late final GeneratedColumn<String> ingredientType = GeneratedColumn<String>(
      'ingredient_type', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('recipe'));
  @override
  List<GeneratedColumn> get $columns => [
        id,
        rowVersion,
        isDeleted,
        lastModifiedHlc,
        isSynced,
        brandId,
        name,
        trackingMode,
        baseUnit,
        unitType,
        buyPrice,
        buyQty,
        costPerBaseUnit,
        ingredientType
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'ingredients';
  @override
  VerificationContext validateIntegrity(Insertable<IngredientLocal> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('row_version')) {
      context.handle(
          _rowVersionMeta,
          rowVersion.isAcceptableOrUnknown(
              data['row_version']!, _rowVersionMeta));
    }
    if (data.containsKey('is_deleted')) {
      context.handle(_isDeletedMeta,
          isDeleted.isAcceptableOrUnknown(data['is_deleted']!, _isDeletedMeta));
    }
    if (data.containsKey('last_modified_hlc')) {
      context.handle(
          _lastModifiedHlcMeta,
          lastModifiedHlc.isAcceptableOrUnknown(
              data['last_modified_hlc']!, _lastModifiedHlcMeta));
    }
    if (data.containsKey('is_synced')) {
      context.handle(_isSyncedMeta,
          isSynced.isAcceptableOrUnknown(data['is_synced']!, _isSyncedMeta));
    }
    if (data.containsKey('brand_id')) {
      context.handle(_brandIdMeta,
          brandId.isAcceptableOrUnknown(data['brand_id']!, _brandIdMeta));
    } else if (isInserting) {
      context.missing(_brandIdMeta);
    }
    if (data.containsKey('name')) {
      context.handle(
          _nameMeta, name.isAcceptableOrUnknown(data['name']!, _nameMeta));
    } else if (isInserting) {
      context.missing(_nameMeta);
    }
    if (data.containsKey('tracking_mode')) {
      context.handle(
          _trackingModeMeta,
          trackingMode.isAcceptableOrUnknown(
              data['tracking_mode']!, _trackingModeMeta));
    } else if (isInserting) {
      context.missing(_trackingModeMeta);
    }
    if (data.containsKey('base_unit')) {
      context.handle(_baseUnitMeta,
          baseUnit.isAcceptableOrUnknown(data['base_unit']!, _baseUnitMeta));
    } else if (isInserting) {
      context.missing(_baseUnitMeta);
    }
    if (data.containsKey('unit_type')) {
      context.handle(_unitTypeMeta,
          unitType.isAcceptableOrUnknown(data['unit_type']!, _unitTypeMeta));
    } else if (isInserting) {
      context.missing(_unitTypeMeta);
    }
    if (data.containsKey('buy_price')) {
      context.handle(_buyPriceMeta,
          buyPrice.isAcceptableOrUnknown(data['buy_price']!, _buyPriceMeta));
    }
    if (data.containsKey('buy_qty')) {
      context.handle(_buyQtyMeta,
          buyQty.isAcceptableOrUnknown(data['buy_qty']!, _buyQtyMeta));
    }
    if (data.containsKey('cost_per_base_unit')) {
      context.handle(
          _costPerBaseUnitMeta,
          costPerBaseUnit.isAcceptableOrUnknown(
              data['cost_per_base_unit']!, _costPerBaseUnitMeta));
    }
    if (data.containsKey('ingredient_type')) {
      context.handle(
          _ingredientTypeMeta,
          ingredientType.isAcceptableOrUnknown(
              data['ingredient_type']!, _ingredientTypeMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  IngredientLocal map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return IngredientLocal(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      rowVersion: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}row_version'])!,
      isDeleted: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_deleted'])!,
      lastModifiedHlc: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}last_modified_hlc']),
      isSynced: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_synced'])!,
      brandId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}brand_id'])!,
      name: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}name'])!,
      trackingMode: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}tracking_mode'])!,
      baseUnit: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}base_unit'])!,
      unitType: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}unit_type'])!,
      buyPrice: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}buy_price'])!,
      buyQty: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}buy_qty'])!,
      costPerBaseUnit: attachedDatabase.typeMapping.read(
          DriftSqlType.double, data['${effectivePrefix}cost_per_base_unit'])!,
      ingredientType: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}ingredient_type'])!,
    );
  }

  @override
  $IngredientsTable createAlias(String alias) {
    return $IngredientsTable(attachedDatabase, alias);
  }
}

class IngredientLocal extends DataClass implements Insertable<IngredientLocal> {
  final String id;
  final int rowVersion;
  final bool isDeleted;
  final String? lastModifiedHlc;
  final bool isSynced;
  final String brandId;
  final String name;
  final String trackingMode;
  final String baseUnit;
  final String unitType;
  final double buyPrice;
  final double buyQty;
  final double costPerBaseUnit;
  final String ingredientType;
  const IngredientLocal(
      {required this.id,
      required this.rowVersion,
      required this.isDeleted,
      this.lastModifiedHlc,
      required this.isSynced,
      required this.brandId,
      required this.name,
      required this.trackingMode,
      required this.baseUnit,
      required this.unitType,
      required this.buyPrice,
      required this.buyQty,
      required this.costPerBaseUnit,
      required this.ingredientType});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['row_version'] = Variable<int>(rowVersion);
    map['is_deleted'] = Variable<bool>(isDeleted);
    if (!nullToAbsent || lastModifiedHlc != null) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc);
    }
    map['is_synced'] = Variable<bool>(isSynced);
    map['brand_id'] = Variable<String>(brandId);
    map['name'] = Variable<String>(name);
    map['tracking_mode'] = Variable<String>(trackingMode);
    map['base_unit'] = Variable<String>(baseUnit);
    map['unit_type'] = Variable<String>(unitType);
    map['buy_price'] = Variable<double>(buyPrice);
    map['buy_qty'] = Variable<double>(buyQty);
    map['cost_per_base_unit'] = Variable<double>(costPerBaseUnit);
    map['ingredient_type'] = Variable<String>(ingredientType);
    return map;
  }

  IngredientsCompanion toCompanion(bool nullToAbsent) {
    return IngredientsCompanion(
      id: Value(id),
      rowVersion: Value(rowVersion),
      isDeleted: Value(isDeleted),
      lastModifiedHlc: lastModifiedHlc == null && nullToAbsent
          ? const Value.absent()
          : Value(lastModifiedHlc),
      isSynced: Value(isSynced),
      brandId: Value(brandId),
      name: Value(name),
      trackingMode: Value(trackingMode),
      baseUnit: Value(baseUnit),
      unitType: Value(unitType),
      buyPrice: Value(buyPrice),
      buyQty: Value(buyQty),
      costPerBaseUnit: Value(costPerBaseUnit),
      ingredientType: Value(ingredientType),
    );
  }

  factory IngredientLocal.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return IngredientLocal(
      id: serializer.fromJson<String>(json['id']),
      rowVersion: serializer.fromJson<int>(json['rowVersion']),
      isDeleted: serializer.fromJson<bool>(json['isDeleted']),
      lastModifiedHlc: serializer.fromJson<String?>(json['lastModifiedHlc']),
      isSynced: serializer.fromJson<bool>(json['isSynced']),
      brandId: serializer.fromJson<String>(json['brandId']),
      name: serializer.fromJson<String>(json['name']),
      trackingMode: serializer.fromJson<String>(json['trackingMode']),
      baseUnit: serializer.fromJson<String>(json['baseUnit']),
      unitType: serializer.fromJson<String>(json['unitType']),
      buyPrice: serializer.fromJson<double>(json['buyPrice']),
      buyQty: serializer.fromJson<double>(json['buyQty']),
      costPerBaseUnit: serializer.fromJson<double>(json['costPerBaseUnit']),
      ingredientType: serializer.fromJson<String>(json['ingredientType']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'rowVersion': serializer.toJson<int>(rowVersion),
      'isDeleted': serializer.toJson<bool>(isDeleted),
      'lastModifiedHlc': serializer.toJson<String?>(lastModifiedHlc),
      'isSynced': serializer.toJson<bool>(isSynced),
      'brandId': serializer.toJson<String>(brandId),
      'name': serializer.toJson<String>(name),
      'trackingMode': serializer.toJson<String>(trackingMode),
      'baseUnit': serializer.toJson<String>(baseUnit),
      'unitType': serializer.toJson<String>(unitType),
      'buyPrice': serializer.toJson<double>(buyPrice),
      'buyQty': serializer.toJson<double>(buyQty),
      'costPerBaseUnit': serializer.toJson<double>(costPerBaseUnit),
      'ingredientType': serializer.toJson<String>(ingredientType),
    };
  }

  IngredientLocal copyWith(
          {String? id,
          int? rowVersion,
          bool? isDeleted,
          Value<String?> lastModifiedHlc = const Value.absent(),
          bool? isSynced,
          String? brandId,
          String? name,
          String? trackingMode,
          String? baseUnit,
          String? unitType,
          double? buyPrice,
          double? buyQty,
          double? costPerBaseUnit,
          String? ingredientType}) =>
      IngredientLocal(
        id: id ?? this.id,
        rowVersion: rowVersion ?? this.rowVersion,
        isDeleted: isDeleted ?? this.isDeleted,
        lastModifiedHlc: lastModifiedHlc.present
            ? lastModifiedHlc.value
            : this.lastModifiedHlc,
        isSynced: isSynced ?? this.isSynced,
        brandId: brandId ?? this.brandId,
        name: name ?? this.name,
        trackingMode: trackingMode ?? this.trackingMode,
        baseUnit: baseUnit ?? this.baseUnit,
        unitType: unitType ?? this.unitType,
        buyPrice: buyPrice ?? this.buyPrice,
        buyQty: buyQty ?? this.buyQty,
        costPerBaseUnit: costPerBaseUnit ?? this.costPerBaseUnit,
        ingredientType: ingredientType ?? this.ingredientType,
      );
  IngredientLocal copyWithCompanion(IngredientsCompanion data) {
    return IngredientLocal(
      id: data.id.present ? data.id.value : this.id,
      rowVersion:
          data.rowVersion.present ? data.rowVersion.value : this.rowVersion,
      isDeleted: data.isDeleted.present ? data.isDeleted.value : this.isDeleted,
      lastModifiedHlc: data.lastModifiedHlc.present
          ? data.lastModifiedHlc.value
          : this.lastModifiedHlc,
      isSynced: data.isSynced.present ? data.isSynced.value : this.isSynced,
      brandId: data.brandId.present ? data.brandId.value : this.brandId,
      name: data.name.present ? data.name.value : this.name,
      trackingMode: data.trackingMode.present
          ? data.trackingMode.value
          : this.trackingMode,
      baseUnit: data.baseUnit.present ? data.baseUnit.value : this.baseUnit,
      unitType: data.unitType.present ? data.unitType.value : this.unitType,
      buyPrice: data.buyPrice.present ? data.buyPrice.value : this.buyPrice,
      buyQty: data.buyQty.present ? data.buyQty.value : this.buyQty,
      costPerBaseUnit: data.costPerBaseUnit.present
          ? data.costPerBaseUnit.value
          : this.costPerBaseUnit,
      ingredientType: data.ingredientType.present
          ? data.ingredientType.value
          : this.ingredientType,
    );
  }

  @override
  String toString() {
    return (StringBuffer('IngredientLocal(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('brandId: $brandId, ')
          ..write('name: $name, ')
          ..write('trackingMode: $trackingMode, ')
          ..write('baseUnit: $baseUnit, ')
          ..write('unitType: $unitType, ')
          ..write('buyPrice: $buyPrice, ')
          ..write('buyQty: $buyQty, ')
          ..write('costPerBaseUnit: $costPerBaseUnit, ')
          ..write('ingredientType: $ingredientType')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
      id,
      rowVersion,
      isDeleted,
      lastModifiedHlc,
      isSynced,
      brandId,
      name,
      trackingMode,
      baseUnit,
      unitType,
      buyPrice,
      buyQty,
      costPerBaseUnit,
      ingredientType);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is IngredientLocal &&
          other.id == this.id &&
          other.rowVersion == this.rowVersion &&
          other.isDeleted == this.isDeleted &&
          other.lastModifiedHlc == this.lastModifiedHlc &&
          other.isSynced == this.isSynced &&
          other.brandId == this.brandId &&
          other.name == this.name &&
          other.trackingMode == this.trackingMode &&
          other.baseUnit == this.baseUnit &&
          other.unitType == this.unitType &&
          other.buyPrice == this.buyPrice &&
          other.buyQty == this.buyQty &&
          other.costPerBaseUnit == this.costPerBaseUnit &&
          other.ingredientType == this.ingredientType);
}

class IngredientsCompanion extends UpdateCompanion<IngredientLocal> {
  final Value<String> id;
  final Value<int> rowVersion;
  final Value<bool> isDeleted;
  final Value<String?> lastModifiedHlc;
  final Value<bool> isSynced;
  final Value<String> brandId;
  final Value<String> name;
  final Value<String> trackingMode;
  final Value<String> baseUnit;
  final Value<String> unitType;
  final Value<double> buyPrice;
  final Value<double> buyQty;
  final Value<double> costPerBaseUnit;
  final Value<String> ingredientType;
  final Value<int> rowid;
  const IngredientsCompanion({
    this.id = const Value.absent(),
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    this.brandId = const Value.absent(),
    this.name = const Value.absent(),
    this.trackingMode = const Value.absent(),
    this.baseUnit = const Value.absent(),
    this.unitType = const Value.absent(),
    this.buyPrice = const Value.absent(),
    this.buyQty = const Value.absent(),
    this.costPerBaseUnit = const Value.absent(),
    this.ingredientType = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  IngredientsCompanion.insert({
    required String id,
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    required String brandId,
    required String name,
    required String trackingMode,
    required String baseUnit,
    required String unitType,
    this.buyPrice = const Value.absent(),
    this.buyQty = const Value.absent(),
    this.costPerBaseUnit = const Value.absent(),
    this.ingredientType = const Value.absent(),
    this.rowid = const Value.absent(),
  })  : id = Value(id),
        brandId = Value(brandId),
        name = Value(name),
        trackingMode = Value(trackingMode),
        baseUnit = Value(baseUnit),
        unitType = Value(unitType);
  static Insertable<IngredientLocal> custom({
    Expression<String>? id,
    Expression<int>? rowVersion,
    Expression<bool>? isDeleted,
    Expression<String>? lastModifiedHlc,
    Expression<bool>? isSynced,
    Expression<String>? brandId,
    Expression<String>? name,
    Expression<String>? trackingMode,
    Expression<String>? baseUnit,
    Expression<String>? unitType,
    Expression<double>? buyPrice,
    Expression<double>? buyQty,
    Expression<double>? costPerBaseUnit,
    Expression<String>? ingredientType,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (rowVersion != null) 'row_version': rowVersion,
      if (isDeleted != null) 'is_deleted': isDeleted,
      if (lastModifiedHlc != null) 'last_modified_hlc': lastModifiedHlc,
      if (isSynced != null) 'is_synced': isSynced,
      if (brandId != null) 'brand_id': brandId,
      if (name != null) 'name': name,
      if (trackingMode != null) 'tracking_mode': trackingMode,
      if (baseUnit != null) 'base_unit': baseUnit,
      if (unitType != null) 'unit_type': unitType,
      if (buyPrice != null) 'buy_price': buyPrice,
      if (buyQty != null) 'buy_qty': buyQty,
      if (costPerBaseUnit != null) 'cost_per_base_unit': costPerBaseUnit,
      if (ingredientType != null) 'ingredient_type': ingredientType,
      if (rowid != null) 'rowid': rowid,
    });
  }

  IngredientsCompanion copyWith(
      {Value<String>? id,
      Value<int>? rowVersion,
      Value<bool>? isDeleted,
      Value<String?>? lastModifiedHlc,
      Value<bool>? isSynced,
      Value<String>? brandId,
      Value<String>? name,
      Value<String>? trackingMode,
      Value<String>? baseUnit,
      Value<String>? unitType,
      Value<double>? buyPrice,
      Value<double>? buyQty,
      Value<double>? costPerBaseUnit,
      Value<String>? ingredientType,
      Value<int>? rowid}) {
    return IngredientsCompanion(
      id: id ?? this.id,
      rowVersion: rowVersion ?? this.rowVersion,
      isDeleted: isDeleted ?? this.isDeleted,
      lastModifiedHlc: lastModifiedHlc ?? this.lastModifiedHlc,
      isSynced: isSynced ?? this.isSynced,
      brandId: brandId ?? this.brandId,
      name: name ?? this.name,
      trackingMode: trackingMode ?? this.trackingMode,
      baseUnit: baseUnit ?? this.baseUnit,
      unitType: unitType ?? this.unitType,
      buyPrice: buyPrice ?? this.buyPrice,
      buyQty: buyQty ?? this.buyQty,
      costPerBaseUnit: costPerBaseUnit ?? this.costPerBaseUnit,
      ingredientType: ingredientType ?? this.ingredientType,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (rowVersion.present) {
      map['row_version'] = Variable<int>(rowVersion.value);
    }
    if (isDeleted.present) {
      map['is_deleted'] = Variable<bool>(isDeleted.value);
    }
    if (lastModifiedHlc.present) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc.value);
    }
    if (isSynced.present) {
      map['is_synced'] = Variable<bool>(isSynced.value);
    }
    if (brandId.present) {
      map['brand_id'] = Variable<String>(brandId.value);
    }
    if (name.present) {
      map['name'] = Variable<String>(name.value);
    }
    if (trackingMode.present) {
      map['tracking_mode'] = Variable<String>(trackingMode.value);
    }
    if (baseUnit.present) {
      map['base_unit'] = Variable<String>(baseUnit.value);
    }
    if (unitType.present) {
      map['unit_type'] = Variable<String>(unitType.value);
    }
    if (buyPrice.present) {
      map['buy_price'] = Variable<double>(buyPrice.value);
    }
    if (buyQty.present) {
      map['buy_qty'] = Variable<double>(buyQty.value);
    }
    if (costPerBaseUnit.present) {
      map['cost_per_base_unit'] = Variable<double>(costPerBaseUnit.value);
    }
    if (ingredientType.present) {
      map['ingredient_type'] = Variable<String>(ingredientType.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('IngredientsCompanion(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('brandId: $brandId, ')
          ..write('name: $name, ')
          ..write('trackingMode: $trackingMode, ')
          ..write('baseUnit: $baseUnit, ')
          ..write('unitType: $unitType, ')
          ..write('buyPrice: $buyPrice, ')
          ..write('buyQty: $buyQty, ')
          ..write('costPerBaseUnit: $costPerBaseUnit, ')
          ..write('ingredientType: $ingredientType, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $RecipesTable extends Recipes with TableInfo<$RecipesTable, RecipeLocal> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $RecipesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
      'id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _rowVersionMeta =
      const VerificationMeta('rowVersion');
  @override
  late final GeneratedColumn<int> rowVersion = GeneratedColumn<int>(
      'row_version', aliasedName, false,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultValue: const Constant(0));
  static const VerificationMeta _isDeletedMeta =
      const VerificationMeta('isDeleted');
  @override
  late final GeneratedColumn<bool> isDeleted = GeneratedColumn<bool>(
      'is_deleted', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_deleted" IN (0, 1))'),
      defaultValue: const Constant(false));
  static const VerificationMeta _lastModifiedHlcMeta =
      const VerificationMeta('lastModifiedHlc');
  @override
  late final GeneratedColumn<String> lastModifiedHlc = GeneratedColumn<String>(
      'last_modified_hlc', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _isSyncedMeta =
      const VerificationMeta('isSynced');
  @override
  late final GeneratedColumn<bool> isSynced = GeneratedColumn<bool>(
      'is_synced', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_synced" IN (0, 1))'),
      defaultValue: const Constant(true));
  static const VerificationMeta _productIdMeta =
      const VerificationMeta('productId');
  @override
  late final GeneratedColumn<String> productId = GeneratedColumn<String>(
      'product_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _versionMeta =
      const VerificationMeta('version');
  @override
  late final GeneratedColumn<int> version = GeneratedColumn<int>(
      'version', aliasedName, false,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultValue: const Constant(1));
  static const VerificationMeta _isActiveMeta =
      const VerificationMeta('isActive');
  @override
  late final GeneratedColumn<bool> isActive = GeneratedColumn<bool>(
      'is_active', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_active" IN (0, 1))'),
      defaultValue: const Constant(true));
  static const VerificationMeta _notesMeta = const VerificationMeta('notes');
  @override
  late final GeneratedColumn<String> notes = GeneratedColumn<String>(
      'notes', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  @override
  List<GeneratedColumn> get $columns => [
        id,
        rowVersion,
        isDeleted,
        lastModifiedHlc,
        isSynced,
        productId,
        version,
        isActive,
        notes
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'recipes';
  @override
  VerificationContext validateIntegrity(Insertable<RecipeLocal> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('row_version')) {
      context.handle(
          _rowVersionMeta,
          rowVersion.isAcceptableOrUnknown(
              data['row_version']!, _rowVersionMeta));
    }
    if (data.containsKey('is_deleted')) {
      context.handle(_isDeletedMeta,
          isDeleted.isAcceptableOrUnknown(data['is_deleted']!, _isDeletedMeta));
    }
    if (data.containsKey('last_modified_hlc')) {
      context.handle(
          _lastModifiedHlcMeta,
          lastModifiedHlc.isAcceptableOrUnknown(
              data['last_modified_hlc']!, _lastModifiedHlcMeta));
    }
    if (data.containsKey('is_synced')) {
      context.handle(_isSyncedMeta,
          isSynced.isAcceptableOrUnknown(data['is_synced']!, _isSyncedMeta));
    }
    if (data.containsKey('product_id')) {
      context.handle(_productIdMeta,
          productId.isAcceptableOrUnknown(data['product_id']!, _productIdMeta));
    } else if (isInserting) {
      context.missing(_productIdMeta);
    }
    if (data.containsKey('version')) {
      context.handle(_versionMeta,
          version.isAcceptableOrUnknown(data['version']!, _versionMeta));
    }
    if (data.containsKey('is_active')) {
      context.handle(_isActiveMeta,
          isActive.isAcceptableOrUnknown(data['is_active']!, _isActiveMeta));
    }
    if (data.containsKey('notes')) {
      context.handle(
          _notesMeta, notes.isAcceptableOrUnknown(data['notes']!, _notesMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  RecipeLocal map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return RecipeLocal(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      rowVersion: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}row_version'])!,
      isDeleted: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_deleted'])!,
      lastModifiedHlc: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}last_modified_hlc']),
      isSynced: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_synced'])!,
      productId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}product_id'])!,
      version: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}version'])!,
      isActive: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_active'])!,
      notes: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}notes']),
    );
  }

  @override
  $RecipesTable createAlias(String alias) {
    return $RecipesTable(attachedDatabase, alias);
  }
}

class RecipeLocal extends DataClass implements Insertable<RecipeLocal> {
  final String id;
  final int rowVersion;
  final bool isDeleted;
  final String? lastModifiedHlc;
  final bool isSynced;
  final String productId;
  final int version;
  final bool isActive;
  final String? notes;
  const RecipeLocal(
      {required this.id,
      required this.rowVersion,
      required this.isDeleted,
      this.lastModifiedHlc,
      required this.isSynced,
      required this.productId,
      required this.version,
      required this.isActive,
      this.notes});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['row_version'] = Variable<int>(rowVersion);
    map['is_deleted'] = Variable<bool>(isDeleted);
    if (!nullToAbsent || lastModifiedHlc != null) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc);
    }
    map['is_synced'] = Variable<bool>(isSynced);
    map['product_id'] = Variable<String>(productId);
    map['version'] = Variable<int>(version);
    map['is_active'] = Variable<bool>(isActive);
    if (!nullToAbsent || notes != null) {
      map['notes'] = Variable<String>(notes);
    }
    return map;
  }

  RecipesCompanion toCompanion(bool nullToAbsent) {
    return RecipesCompanion(
      id: Value(id),
      rowVersion: Value(rowVersion),
      isDeleted: Value(isDeleted),
      lastModifiedHlc: lastModifiedHlc == null && nullToAbsent
          ? const Value.absent()
          : Value(lastModifiedHlc),
      isSynced: Value(isSynced),
      productId: Value(productId),
      version: Value(version),
      isActive: Value(isActive),
      notes:
          notes == null && nullToAbsent ? const Value.absent() : Value(notes),
    );
  }

  factory RecipeLocal.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return RecipeLocal(
      id: serializer.fromJson<String>(json['id']),
      rowVersion: serializer.fromJson<int>(json['rowVersion']),
      isDeleted: serializer.fromJson<bool>(json['isDeleted']),
      lastModifiedHlc: serializer.fromJson<String?>(json['lastModifiedHlc']),
      isSynced: serializer.fromJson<bool>(json['isSynced']),
      productId: serializer.fromJson<String>(json['productId']),
      version: serializer.fromJson<int>(json['version']),
      isActive: serializer.fromJson<bool>(json['isActive']),
      notes: serializer.fromJson<String?>(json['notes']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'rowVersion': serializer.toJson<int>(rowVersion),
      'isDeleted': serializer.toJson<bool>(isDeleted),
      'lastModifiedHlc': serializer.toJson<String?>(lastModifiedHlc),
      'isSynced': serializer.toJson<bool>(isSynced),
      'productId': serializer.toJson<String>(productId),
      'version': serializer.toJson<int>(version),
      'isActive': serializer.toJson<bool>(isActive),
      'notes': serializer.toJson<String?>(notes),
    };
  }

  RecipeLocal copyWith(
          {String? id,
          int? rowVersion,
          bool? isDeleted,
          Value<String?> lastModifiedHlc = const Value.absent(),
          bool? isSynced,
          String? productId,
          int? version,
          bool? isActive,
          Value<String?> notes = const Value.absent()}) =>
      RecipeLocal(
        id: id ?? this.id,
        rowVersion: rowVersion ?? this.rowVersion,
        isDeleted: isDeleted ?? this.isDeleted,
        lastModifiedHlc: lastModifiedHlc.present
            ? lastModifiedHlc.value
            : this.lastModifiedHlc,
        isSynced: isSynced ?? this.isSynced,
        productId: productId ?? this.productId,
        version: version ?? this.version,
        isActive: isActive ?? this.isActive,
        notes: notes.present ? notes.value : this.notes,
      );
  RecipeLocal copyWithCompanion(RecipesCompanion data) {
    return RecipeLocal(
      id: data.id.present ? data.id.value : this.id,
      rowVersion:
          data.rowVersion.present ? data.rowVersion.value : this.rowVersion,
      isDeleted: data.isDeleted.present ? data.isDeleted.value : this.isDeleted,
      lastModifiedHlc: data.lastModifiedHlc.present
          ? data.lastModifiedHlc.value
          : this.lastModifiedHlc,
      isSynced: data.isSynced.present ? data.isSynced.value : this.isSynced,
      productId: data.productId.present ? data.productId.value : this.productId,
      version: data.version.present ? data.version.value : this.version,
      isActive: data.isActive.present ? data.isActive.value : this.isActive,
      notes: data.notes.present ? data.notes.value : this.notes,
    );
  }

  @override
  String toString() {
    return (StringBuffer('RecipeLocal(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('productId: $productId, ')
          ..write('version: $version, ')
          ..write('isActive: $isActive, ')
          ..write('notes: $notes')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, rowVersion, isDeleted, lastModifiedHlc,
      isSynced, productId, version, isActive, notes);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is RecipeLocal &&
          other.id == this.id &&
          other.rowVersion == this.rowVersion &&
          other.isDeleted == this.isDeleted &&
          other.lastModifiedHlc == this.lastModifiedHlc &&
          other.isSynced == this.isSynced &&
          other.productId == this.productId &&
          other.version == this.version &&
          other.isActive == this.isActive &&
          other.notes == this.notes);
}

class RecipesCompanion extends UpdateCompanion<RecipeLocal> {
  final Value<String> id;
  final Value<int> rowVersion;
  final Value<bool> isDeleted;
  final Value<String?> lastModifiedHlc;
  final Value<bool> isSynced;
  final Value<String> productId;
  final Value<int> version;
  final Value<bool> isActive;
  final Value<String?> notes;
  final Value<int> rowid;
  const RecipesCompanion({
    this.id = const Value.absent(),
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    this.productId = const Value.absent(),
    this.version = const Value.absent(),
    this.isActive = const Value.absent(),
    this.notes = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  RecipesCompanion.insert({
    required String id,
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    required String productId,
    this.version = const Value.absent(),
    this.isActive = const Value.absent(),
    this.notes = const Value.absent(),
    this.rowid = const Value.absent(),
  })  : id = Value(id),
        productId = Value(productId);
  static Insertable<RecipeLocal> custom({
    Expression<String>? id,
    Expression<int>? rowVersion,
    Expression<bool>? isDeleted,
    Expression<String>? lastModifiedHlc,
    Expression<bool>? isSynced,
    Expression<String>? productId,
    Expression<int>? version,
    Expression<bool>? isActive,
    Expression<String>? notes,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (rowVersion != null) 'row_version': rowVersion,
      if (isDeleted != null) 'is_deleted': isDeleted,
      if (lastModifiedHlc != null) 'last_modified_hlc': lastModifiedHlc,
      if (isSynced != null) 'is_synced': isSynced,
      if (productId != null) 'product_id': productId,
      if (version != null) 'version': version,
      if (isActive != null) 'is_active': isActive,
      if (notes != null) 'notes': notes,
      if (rowid != null) 'rowid': rowid,
    });
  }

  RecipesCompanion copyWith(
      {Value<String>? id,
      Value<int>? rowVersion,
      Value<bool>? isDeleted,
      Value<String?>? lastModifiedHlc,
      Value<bool>? isSynced,
      Value<String>? productId,
      Value<int>? version,
      Value<bool>? isActive,
      Value<String?>? notes,
      Value<int>? rowid}) {
    return RecipesCompanion(
      id: id ?? this.id,
      rowVersion: rowVersion ?? this.rowVersion,
      isDeleted: isDeleted ?? this.isDeleted,
      lastModifiedHlc: lastModifiedHlc ?? this.lastModifiedHlc,
      isSynced: isSynced ?? this.isSynced,
      productId: productId ?? this.productId,
      version: version ?? this.version,
      isActive: isActive ?? this.isActive,
      notes: notes ?? this.notes,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (rowVersion.present) {
      map['row_version'] = Variable<int>(rowVersion.value);
    }
    if (isDeleted.present) {
      map['is_deleted'] = Variable<bool>(isDeleted.value);
    }
    if (lastModifiedHlc.present) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc.value);
    }
    if (isSynced.present) {
      map['is_synced'] = Variable<bool>(isSynced.value);
    }
    if (productId.present) {
      map['product_id'] = Variable<String>(productId.value);
    }
    if (version.present) {
      map['version'] = Variable<int>(version.value);
    }
    if (isActive.present) {
      map['is_active'] = Variable<bool>(isActive.value);
    }
    if (notes.present) {
      map['notes'] = Variable<String>(notes.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('RecipesCompanion(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('productId: $productId, ')
          ..write('version: $version, ')
          ..write('isActive: $isActive, ')
          ..write('notes: $notes, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $RecipeIngredientsTable extends RecipeIngredients
    with TableInfo<$RecipeIngredientsTable, RecipeIngredientLocal> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $RecipeIngredientsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
      'id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _rowVersionMeta =
      const VerificationMeta('rowVersion');
  @override
  late final GeneratedColumn<int> rowVersion = GeneratedColumn<int>(
      'row_version', aliasedName, false,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultValue: const Constant(0));
  static const VerificationMeta _isDeletedMeta =
      const VerificationMeta('isDeleted');
  @override
  late final GeneratedColumn<bool> isDeleted = GeneratedColumn<bool>(
      'is_deleted', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_deleted" IN (0, 1))'),
      defaultValue: const Constant(false));
  static const VerificationMeta _lastModifiedHlcMeta =
      const VerificationMeta('lastModifiedHlc');
  @override
  late final GeneratedColumn<String> lastModifiedHlc = GeneratedColumn<String>(
      'last_modified_hlc', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _isSyncedMeta =
      const VerificationMeta('isSynced');
  @override
  late final GeneratedColumn<bool> isSynced = GeneratedColumn<bool>(
      'is_synced', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_synced" IN (0, 1))'),
      defaultValue: const Constant(true));
  static const VerificationMeta _recipeIdMeta =
      const VerificationMeta('recipeId');
  @override
  late final GeneratedColumn<String> recipeId = GeneratedColumn<String>(
      'recipe_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _ingredientIdMeta =
      const VerificationMeta('ingredientId');
  @override
  late final GeneratedColumn<String> ingredientId = GeneratedColumn<String>(
      'ingredient_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _quantityMeta =
      const VerificationMeta('quantity');
  @override
  late final GeneratedColumn<double> quantity = GeneratedColumn<double>(
      'quantity', aliasedName, false,
      type: DriftSqlType.double, requiredDuringInsert: true);
  static const VerificationMeta _quantityUnitMeta =
      const VerificationMeta('quantityUnit');
  @override
  late final GeneratedColumn<String> quantityUnit = GeneratedColumn<String>(
      'quantity_unit', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _notesMeta = const VerificationMeta('notes');
  @override
  late final GeneratedColumn<String> notes = GeneratedColumn<String>(
      'notes', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _isOptionalMeta =
      const VerificationMeta('isOptional');
  @override
  late final GeneratedColumn<bool> isOptional = GeneratedColumn<bool>(
      'is_optional', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_optional" IN (0, 1))'),
      defaultValue: const Constant(false));
  @override
  List<GeneratedColumn> get $columns => [
        id,
        rowVersion,
        isDeleted,
        lastModifiedHlc,
        isSynced,
        recipeId,
        ingredientId,
        quantity,
        quantityUnit,
        notes,
        isOptional
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'recipe_ingredients';
  @override
  VerificationContext validateIntegrity(
      Insertable<RecipeIngredientLocal> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('row_version')) {
      context.handle(
          _rowVersionMeta,
          rowVersion.isAcceptableOrUnknown(
              data['row_version']!, _rowVersionMeta));
    }
    if (data.containsKey('is_deleted')) {
      context.handle(_isDeletedMeta,
          isDeleted.isAcceptableOrUnknown(data['is_deleted']!, _isDeletedMeta));
    }
    if (data.containsKey('last_modified_hlc')) {
      context.handle(
          _lastModifiedHlcMeta,
          lastModifiedHlc.isAcceptableOrUnknown(
              data['last_modified_hlc']!, _lastModifiedHlcMeta));
    }
    if (data.containsKey('is_synced')) {
      context.handle(_isSyncedMeta,
          isSynced.isAcceptableOrUnknown(data['is_synced']!, _isSyncedMeta));
    }
    if (data.containsKey('recipe_id')) {
      context.handle(_recipeIdMeta,
          recipeId.isAcceptableOrUnknown(data['recipe_id']!, _recipeIdMeta));
    } else if (isInserting) {
      context.missing(_recipeIdMeta);
    }
    if (data.containsKey('ingredient_id')) {
      context.handle(
          _ingredientIdMeta,
          ingredientId.isAcceptableOrUnknown(
              data['ingredient_id']!, _ingredientIdMeta));
    } else if (isInserting) {
      context.missing(_ingredientIdMeta);
    }
    if (data.containsKey('quantity')) {
      context.handle(_quantityMeta,
          quantity.isAcceptableOrUnknown(data['quantity']!, _quantityMeta));
    } else if (isInserting) {
      context.missing(_quantityMeta);
    }
    if (data.containsKey('quantity_unit')) {
      context.handle(
          _quantityUnitMeta,
          quantityUnit.isAcceptableOrUnknown(
              data['quantity_unit']!, _quantityUnitMeta));
    } else if (isInserting) {
      context.missing(_quantityUnitMeta);
    }
    if (data.containsKey('notes')) {
      context.handle(
          _notesMeta, notes.isAcceptableOrUnknown(data['notes']!, _notesMeta));
    }
    if (data.containsKey('is_optional')) {
      context.handle(
          _isOptionalMeta,
          isOptional.isAcceptableOrUnknown(
              data['is_optional']!, _isOptionalMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  RecipeIngredientLocal map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return RecipeIngredientLocal(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      rowVersion: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}row_version'])!,
      isDeleted: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_deleted'])!,
      lastModifiedHlc: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}last_modified_hlc']),
      isSynced: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_synced'])!,
      recipeId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}recipe_id'])!,
      ingredientId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}ingredient_id'])!,
      quantity: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}quantity'])!,
      quantityUnit: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}quantity_unit'])!,
      notes: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}notes']),
      isOptional: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_optional'])!,
    );
  }

  @override
  $RecipeIngredientsTable createAlias(String alias) {
    return $RecipeIngredientsTable(attachedDatabase, alias);
  }
}

class RecipeIngredientLocal extends DataClass
    implements Insertable<RecipeIngredientLocal> {
  final String id;
  final int rowVersion;
  final bool isDeleted;
  final String? lastModifiedHlc;
  final bool isSynced;
  final String recipeId;
  final String ingredientId;
  final double quantity;
  final String quantityUnit;
  final String? notes;
  final bool isOptional;
  const RecipeIngredientLocal(
      {required this.id,
      required this.rowVersion,
      required this.isDeleted,
      this.lastModifiedHlc,
      required this.isSynced,
      required this.recipeId,
      required this.ingredientId,
      required this.quantity,
      required this.quantityUnit,
      this.notes,
      required this.isOptional});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['row_version'] = Variable<int>(rowVersion);
    map['is_deleted'] = Variable<bool>(isDeleted);
    if (!nullToAbsent || lastModifiedHlc != null) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc);
    }
    map['is_synced'] = Variable<bool>(isSynced);
    map['recipe_id'] = Variable<String>(recipeId);
    map['ingredient_id'] = Variable<String>(ingredientId);
    map['quantity'] = Variable<double>(quantity);
    map['quantity_unit'] = Variable<String>(quantityUnit);
    if (!nullToAbsent || notes != null) {
      map['notes'] = Variable<String>(notes);
    }
    map['is_optional'] = Variable<bool>(isOptional);
    return map;
  }

  RecipeIngredientsCompanion toCompanion(bool nullToAbsent) {
    return RecipeIngredientsCompanion(
      id: Value(id),
      rowVersion: Value(rowVersion),
      isDeleted: Value(isDeleted),
      lastModifiedHlc: lastModifiedHlc == null && nullToAbsent
          ? const Value.absent()
          : Value(lastModifiedHlc),
      isSynced: Value(isSynced),
      recipeId: Value(recipeId),
      ingredientId: Value(ingredientId),
      quantity: Value(quantity),
      quantityUnit: Value(quantityUnit),
      notes:
          notes == null && nullToAbsent ? const Value.absent() : Value(notes),
      isOptional: Value(isOptional),
    );
  }

  factory RecipeIngredientLocal.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return RecipeIngredientLocal(
      id: serializer.fromJson<String>(json['id']),
      rowVersion: serializer.fromJson<int>(json['rowVersion']),
      isDeleted: serializer.fromJson<bool>(json['isDeleted']),
      lastModifiedHlc: serializer.fromJson<String?>(json['lastModifiedHlc']),
      isSynced: serializer.fromJson<bool>(json['isSynced']),
      recipeId: serializer.fromJson<String>(json['recipeId']),
      ingredientId: serializer.fromJson<String>(json['ingredientId']),
      quantity: serializer.fromJson<double>(json['quantity']),
      quantityUnit: serializer.fromJson<String>(json['quantityUnit']),
      notes: serializer.fromJson<String?>(json['notes']),
      isOptional: serializer.fromJson<bool>(json['isOptional']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'rowVersion': serializer.toJson<int>(rowVersion),
      'isDeleted': serializer.toJson<bool>(isDeleted),
      'lastModifiedHlc': serializer.toJson<String?>(lastModifiedHlc),
      'isSynced': serializer.toJson<bool>(isSynced),
      'recipeId': serializer.toJson<String>(recipeId),
      'ingredientId': serializer.toJson<String>(ingredientId),
      'quantity': serializer.toJson<double>(quantity),
      'quantityUnit': serializer.toJson<String>(quantityUnit),
      'notes': serializer.toJson<String?>(notes),
      'isOptional': serializer.toJson<bool>(isOptional),
    };
  }

  RecipeIngredientLocal copyWith(
          {String? id,
          int? rowVersion,
          bool? isDeleted,
          Value<String?> lastModifiedHlc = const Value.absent(),
          bool? isSynced,
          String? recipeId,
          String? ingredientId,
          double? quantity,
          String? quantityUnit,
          Value<String?> notes = const Value.absent(),
          bool? isOptional}) =>
      RecipeIngredientLocal(
        id: id ?? this.id,
        rowVersion: rowVersion ?? this.rowVersion,
        isDeleted: isDeleted ?? this.isDeleted,
        lastModifiedHlc: lastModifiedHlc.present
            ? lastModifiedHlc.value
            : this.lastModifiedHlc,
        isSynced: isSynced ?? this.isSynced,
        recipeId: recipeId ?? this.recipeId,
        ingredientId: ingredientId ?? this.ingredientId,
        quantity: quantity ?? this.quantity,
        quantityUnit: quantityUnit ?? this.quantityUnit,
        notes: notes.present ? notes.value : this.notes,
        isOptional: isOptional ?? this.isOptional,
      );
  RecipeIngredientLocal copyWithCompanion(RecipeIngredientsCompanion data) {
    return RecipeIngredientLocal(
      id: data.id.present ? data.id.value : this.id,
      rowVersion:
          data.rowVersion.present ? data.rowVersion.value : this.rowVersion,
      isDeleted: data.isDeleted.present ? data.isDeleted.value : this.isDeleted,
      lastModifiedHlc: data.lastModifiedHlc.present
          ? data.lastModifiedHlc.value
          : this.lastModifiedHlc,
      isSynced: data.isSynced.present ? data.isSynced.value : this.isSynced,
      recipeId: data.recipeId.present ? data.recipeId.value : this.recipeId,
      ingredientId: data.ingredientId.present
          ? data.ingredientId.value
          : this.ingredientId,
      quantity: data.quantity.present ? data.quantity.value : this.quantity,
      quantityUnit: data.quantityUnit.present
          ? data.quantityUnit.value
          : this.quantityUnit,
      notes: data.notes.present ? data.notes.value : this.notes,
      isOptional:
          data.isOptional.present ? data.isOptional.value : this.isOptional,
    );
  }

  @override
  String toString() {
    return (StringBuffer('RecipeIngredientLocal(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('recipeId: $recipeId, ')
          ..write('ingredientId: $ingredientId, ')
          ..write('quantity: $quantity, ')
          ..write('quantityUnit: $quantityUnit, ')
          ..write('notes: $notes, ')
          ..write('isOptional: $isOptional')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
      id,
      rowVersion,
      isDeleted,
      lastModifiedHlc,
      isSynced,
      recipeId,
      ingredientId,
      quantity,
      quantityUnit,
      notes,
      isOptional);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is RecipeIngredientLocal &&
          other.id == this.id &&
          other.rowVersion == this.rowVersion &&
          other.isDeleted == this.isDeleted &&
          other.lastModifiedHlc == this.lastModifiedHlc &&
          other.isSynced == this.isSynced &&
          other.recipeId == this.recipeId &&
          other.ingredientId == this.ingredientId &&
          other.quantity == this.quantity &&
          other.quantityUnit == this.quantityUnit &&
          other.notes == this.notes &&
          other.isOptional == this.isOptional);
}

class RecipeIngredientsCompanion
    extends UpdateCompanion<RecipeIngredientLocal> {
  final Value<String> id;
  final Value<int> rowVersion;
  final Value<bool> isDeleted;
  final Value<String?> lastModifiedHlc;
  final Value<bool> isSynced;
  final Value<String> recipeId;
  final Value<String> ingredientId;
  final Value<double> quantity;
  final Value<String> quantityUnit;
  final Value<String?> notes;
  final Value<bool> isOptional;
  final Value<int> rowid;
  const RecipeIngredientsCompanion({
    this.id = const Value.absent(),
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    this.recipeId = const Value.absent(),
    this.ingredientId = const Value.absent(),
    this.quantity = const Value.absent(),
    this.quantityUnit = const Value.absent(),
    this.notes = const Value.absent(),
    this.isOptional = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  RecipeIngredientsCompanion.insert({
    required String id,
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    required String recipeId,
    required String ingredientId,
    required double quantity,
    required String quantityUnit,
    this.notes = const Value.absent(),
    this.isOptional = const Value.absent(),
    this.rowid = const Value.absent(),
  })  : id = Value(id),
        recipeId = Value(recipeId),
        ingredientId = Value(ingredientId),
        quantity = Value(quantity),
        quantityUnit = Value(quantityUnit);
  static Insertable<RecipeIngredientLocal> custom({
    Expression<String>? id,
    Expression<int>? rowVersion,
    Expression<bool>? isDeleted,
    Expression<String>? lastModifiedHlc,
    Expression<bool>? isSynced,
    Expression<String>? recipeId,
    Expression<String>? ingredientId,
    Expression<double>? quantity,
    Expression<String>? quantityUnit,
    Expression<String>? notes,
    Expression<bool>? isOptional,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (rowVersion != null) 'row_version': rowVersion,
      if (isDeleted != null) 'is_deleted': isDeleted,
      if (lastModifiedHlc != null) 'last_modified_hlc': lastModifiedHlc,
      if (isSynced != null) 'is_synced': isSynced,
      if (recipeId != null) 'recipe_id': recipeId,
      if (ingredientId != null) 'ingredient_id': ingredientId,
      if (quantity != null) 'quantity': quantity,
      if (quantityUnit != null) 'quantity_unit': quantityUnit,
      if (notes != null) 'notes': notes,
      if (isOptional != null) 'is_optional': isOptional,
      if (rowid != null) 'rowid': rowid,
    });
  }

  RecipeIngredientsCompanion copyWith(
      {Value<String>? id,
      Value<int>? rowVersion,
      Value<bool>? isDeleted,
      Value<String?>? lastModifiedHlc,
      Value<bool>? isSynced,
      Value<String>? recipeId,
      Value<String>? ingredientId,
      Value<double>? quantity,
      Value<String>? quantityUnit,
      Value<String?>? notes,
      Value<bool>? isOptional,
      Value<int>? rowid}) {
    return RecipeIngredientsCompanion(
      id: id ?? this.id,
      rowVersion: rowVersion ?? this.rowVersion,
      isDeleted: isDeleted ?? this.isDeleted,
      lastModifiedHlc: lastModifiedHlc ?? this.lastModifiedHlc,
      isSynced: isSynced ?? this.isSynced,
      recipeId: recipeId ?? this.recipeId,
      ingredientId: ingredientId ?? this.ingredientId,
      quantity: quantity ?? this.quantity,
      quantityUnit: quantityUnit ?? this.quantityUnit,
      notes: notes ?? this.notes,
      isOptional: isOptional ?? this.isOptional,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (rowVersion.present) {
      map['row_version'] = Variable<int>(rowVersion.value);
    }
    if (isDeleted.present) {
      map['is_deleted'] = Variable<bool>(isDeleted.value);
    }
    if (lastModifiedHlc.present) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc.value);
    }
    if (isSynced.present) {
      map['is_synced'] = Variable<bool>(isSynced.value);
    }
    if (recipeId.present) {
      map['recipe_id'] = Variable<String>(recipeId.value);
    }
    if (ingredientId.present) {
      map['ingredient_id'] = Variable<String>(ingredientId.value);
    }
    if (quantity.present) {
      map['quantity'] = Variable<double>(quantity.value);
    }
    if (quantityUnit.present) {
      map['quantity_unit'] = Variable<String>(quantityUnit.value);
    }
    if (notes.present) {
      map['notes'] = Variable<String>(notes.value);
    }
    if (isOptional.present) {
      map['is_optional'] = Variable<bool>(isOptional.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('RecipeIngredientsCompanion(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('recipeId: $recipeId, ')
          ..write('ingredientId: $ingredientId, ')
          ..write('quantity: $quantity, ')
          ..write('quantityUnit: $quantityUnit, ')
          ..write('notes: $notes, ')
          ..write('isOptional: $isOptional, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $OutletStocksTable extends OutletStocks
    with TableInfo<$OutletStocksTable, OutletStockLocal> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $OutletStocksTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
      'id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _rowVersionMeta =
      const VerificationMeta('rowVersion');
  @override
  late final GeneratedColumn<int> rowVersion = GeneratedColumn<int>(
      'row_version', aliasedName, false,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultValue: const Constant(0));
  static const VerificationMeta _isDeletedMeta =
      const VerificationMeta('isDeleted');
  @override
  late final GeneratedColumn<bool> isDeleted = GeneratedColumn<bool>(
      'is_deleted', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_deleted" IN (0, 1))'),
      defaultValue: const Constant(false));
  static const VerificationMeta _lastModifiedHlcMeta =
      const VerificationMeta('lastModifiedHlc');
  @override
  late final GeneratedColumn<String> lastModifiedHlc = GeneratedColumn<String>(
      'last_modified_hlc', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _isSyncedMeta =
      const VerificationMeta('isSynced');
  @override
  late final GeneratedColumn<bool> isSynced = GeneratedColumn<bool>(
      'is_synced', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_synced" IN (0, 1))'),
      defaultValue: const Constant(true));
  static const VerificationMeta _outletIdMeta =
      const VerificationMeta('outletId');
  @override
  late final GeneratedColumn<String> outletId = GeneratedColumn<String>(
      'outlet_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _ingredientIdMeta =
      const VerificationMeta('ingredientId');
  @override
  late final GeneratedColumn<String> ingredientId = GeneratedColumn<String>(
      'ingredient_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _computedStockMeta =
      const VerificationMeta('computedStock');
  @override
  late final GeneratedColumn<double> computedStock = GeneratedColumn<double>(
      'computed_stock', aliasedName, false,
      type: DriftSqlType.double,
      requiredDuringInsert: false,
      defaultValue: const Constant(0.0));
  static const VerificationMeta _minStockBaseMeta =
      const VerificationMeta('minStockBase');
  @override
  late final GeneratedColumn<double> minStockBase = GeneratedColumn<double>(
      'min_stock_base', aliasedName, false,
      type: DriftSqlType.double,
      requiredDuringInsert: false,
      defaultValue: const Constant(0.0));
  @override
  List<GeneratedColumn> get $columns => [
        id,
        rowVersion,
        isDeleted,
        lastModifiedHlc,
        isSynced,
        outletId,
        ingredientId,
        computedStock,
        minStockBase
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'outlet_stocks';
  @override
  VerificationContext validateIntegrity(Insertable<OutletStockLocal> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('row_version')) {
      context.handle(
          _rowVersionMeta,
          rowVersion.isAcceptableOrUnknown(
              data['row_version']!, _rowVersionMeta));
    }
    if (data.containsKey('is_deleted')) {
      context.handle(_isDeletedMeta,
          isDeleted.isAcceptableOrUnknown(data['is_deleted']!, _isDeletedMeta));
    }
    if (data.containsKey('last_modified_hlc')) {
      context.handle(
          _lastModifiedHlcMeta,
          lastModifiedHlc.isAcceptableOrUnknown(
              data['last_modified_hlc']!, _lastModifiedHlcMeta));
    }
    if (data.containsKey('is_synced')) {
      context.handle(_isSyncedMeta,
          isSynced.isAcceptableOrUnknown(data['is_synced']!, _isSyncedMeta));
    }
    if (data.containsKey('outlet_id')) {
      context.handle(_outletIdMeta,
          outletId.isAcceptableOrUnknown(data['outlet_id']!, _outletIdMeta));
    } else if (isInserting) {
      context.missing(_outletIdMeta);
    }
    if (data.containsKey('ingredient_id')) {
      context.handle(
          _ingredientIdMeta,
          ingredientId.isAcceptableOrUnknown(
              data['ingredient_id']!, _ingredientIdMeta));
    } else if (isInserting) {
      context.missing(_ingredientIdMeta);
    }
    if (data.containsKey('computed_stock')) {
      context.handle(
          _computedStockMeta,
          computedStock.isAcceptableOrUnknown(
              data['computed_stock']!, _computedStockMeta));
    }
    if (data.containsKey('min_stock_base')) {
      context.handle(
          _minStockBaseMeta,
          minStockBase.isAcceptableOrUnknown(
              data['min_stock_base']!, _minStockBaseMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  OutletStockLocal map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return OutletStockLocal(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      rowVersion: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}row_version'])!,
      isDeleted: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_deleted'])!,
      lastModifiedHlc: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}last_modified_hlc']),
      isSynced: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_synced'])!,
      outletId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}outlet_id'])!,
      ingredientId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}ingredient_id'])!,
      computedStock: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}computed_stock'])!,
      minStockBase: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}min_stock_base'])!,
    );
  }

  @override
  $OutletStocksTable createAlias(String alias) {
    return $OutletStocksTable(attachedDatabase, alias);
  }
}

class OutletStockLocal extends DataClass
    implements Insertable<OutletStockLocal> {
  final String id;
  final int rowVersion;
  final bool isDeleted;
  final String? lastModifiedHlc;
  final bool isSynced;
  final String outletId;
  final String ingredientId;
  final double computedStock;
  final double minStockBase;
  const OutletStockLocal(
      {required this.id,
      required this.rowVersion,
      required this.isDeleted,
      this.lastModifiedHlc,
      required this.isSynced,
      required this.outletId,
      required this.ingredientId,
      required this.computedStock,
      required this.minStockBase});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['row_version'] = Variable<int>(rowVersion);
    map['is_deleted'] = Variable<bool>(isDeleted);
    if (!nullToAbsent || lastModifiedHlc != null) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc);
    }
    map['is_synced'] = Variable<bool>(isSynced);
    map['outlet_id'] = Variable<String>(outletId);
    map['ingredient_id'] = Variable<String>(ingredientId);
    map['computed_stock'] = Variable<double>(computedStock);
    map['min_stock_base'] = Variable<double>(minStockBase);
    return map;
  }

  OutletStocksCompanion toCompanion(bool nullToAbsent) {
    return OutletStocksCompanion(
      id: Value(id),
      rowVersion: Value(rowVersion),
      isDeleted: Value(isDeleted),
      lastModifiedHlc: lastModifiedHlc == null && nullToAbsent
          ? const Value.absent()
          : Value(lastModifiedHlc),
      isSynced: Value(isSynced),
      outletId: Value(outletId),
      ingredientId: Value(ingredientId),
      computedStock: Value(computedStock),
      minStockBase: Value(minStockBase),
    );
  }

  factory OutletStockLocal.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return OutletStockLocal(
      id: serializer.fromJson<String>(json['id']),
      rowVersion: serializer.fromJson<int>(json['rowVersion']),
      isDeleted: serializer.fromJson<bool>(json['isDeleted']),
      lastModifiedHlc: serializer.fromJson<String?>(json['lastModifiedHlc']),
      isSynced: serializer.fromJson<bool>(json['isSynced']),
      outletId: serializer.fromJson<String>(json['outletId']),
      ingredientId: serializer.fromJson<String>(json['ingredientId']),
      computedStock: serializer.fromJson<double>(json['computedStock']),
      minStockBase: serializer.fromJson<double>(json['minStockBase']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'rowVersion': serializer.toJson<int>(rowVersion),
      'isDeleted': serializer.toJson<bool>(isDeleted),
      'lastModifiedHlc': serializer.toJson<String?>(lastModifiedHlc),
      'isSynced': serializer.toJson<bool>(isSynced),
      'outletId': serializer.toJson<String>(outletId),
      'ingredientId': serializer.toJson<String>(ingredientId),
      'computedStock': serializer.toJson<double>(computedStock),
      'minStockBase': serializer.toJson<double>(minStockBase),
    };
  }

  OutletStockLocal copyWith(
          {String? id,
          int? rowVersion,
          bool? isDeleted,
          Value<String?> lastModifiedHlc = const Value.absent(),
          bool? isSynced,
          String? outletId,
          String? ingredientId,
          double? computedStock,
          double? minStockBase}) =>
      OutletStockLocal(
        id: id ?? this.id,
        rowVersion: rowVersion ?? this.rowVersion,
        isDeleted: isDeleted ?? this.isDeleted,
        lastModifiedHlc: lastModifiedHlc.present
            ? lastModifiedHlc.value
            : this.lastModifiedHlc,
        isSynced: isSynced ?? this.isSynced,
        outletId: outletId ?? this.outletId,
        ingredientId: ingredientId ?? this.ingredientId,
        computedStock: computedStock ?? this.computedStock,
        minStockBase: minStockBase ?? this.minStockBase,
      );
  OutletStockLocal copyWithCompanion(OutletStocksCompanion data) {
    return OutletStockLocal(
      id: data.id.present ? data.id.value : this.id,
      rowVersion:
          data.rowVersion.present ? data.rowVersion.value : this.rowVersion,
      isDeleted: data.isDeleted.present ? data.isDeleted.value : this.isDeleted,
      lastModifiedHlc: data.lastModifiedHlc.present
          ? data.lastModifiedHlc.value
          : this.lastModifiedHlc,
      isSynced: data.isSynced.present ? data.isSynced.value : this.isSynced,
      outletId: data.outletId.present ? data.outletId.value : this.outletId,
      ingredientId: data.ingredientId.present
          ? data.ingredientId.value
          : this.ingredientId,
      computedStock: data.computedStock.present
          ? data.computedStock.value
          : this.computedStock,
      minStockBase: data.minStockBase.present
          ? data.minStockBase.value
          : this.minStockBase,
    );
  }

  @override
  String toString() {
    return (StringBuffer('OutletStockLocal(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('outletId: $outletId, ')
          ..write('ingredientId: $ingredientId, ')
          ..write('computedStock: $computedStock, ')
          ..write('minStockBase: $minStockBase')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, rowVersion, isDeleted, lastModifiedHlc,
      isSynced, outletId, ingredientId, computedStock, minStockBase);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is OutletStockLocal &&
          other.id == this.id &&
          other.rowVersion == this.rowVersion &&
          other.isDeleted == this.isDeleted &&
          other.lastModifiedHlc == this.lastModifiedHlc &&
          other.isSynced == this.isSynced &&
          other.outletId == this.outletId &&
          other.ingredientId == this.ingredientId &&
          other.computedStock == this.computedStock &&
          other.minStockBase == this.minStockBase);
}

class OutletStocksCompanion extends UpdateCompanion<OutletStockLocal> {
  final Value<String> id;
  final Value<int> rowVersion;
  final Value<bool> isDeleted;
  final Value<String?> lastModifiedHlc;
  final Value<bool> isSynced;
  final Value<String> outletId;
  final Value<String> ingredientId;
  final Value<double> computedStock;
  final Value<double> minStockBase;
  final Value<int> rowid;
  const OutletStocksCompanion({
    this.id = const Value.absent(),
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    this.outletId = const Value.absent(),
    this.ingredientId = const Value.absent(),
    this.computedStock = const Value.absent(),
    this.minStockBase = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  OutletStocksCompanion.insert({
    required String id,
    this.rowVersion = const Value.absent(),
    this.isDeleted = const Value.absent(),
    this.lastModifiedHlc = const Value.absent(),
    this.isSynced = const Value.absent(),
    required String outletId,
    required String ingredientId,
    this.computedStock = const Value.absent(),
    this.minStockBase = const Value.absent(),
    this.rowid = const Value.absent(),
  })  : id = Value(id),
        outletId = Value(outletId),
        ingredientId = Value(ingredientId);
  static Insertable<OutletStockLocal> custom({
    Expression<String>? id,
    Expression<int>? rowVersion,
    Expression<bool>? isDeleted,
    Expression<String>? lastModifiedHlc,
    Expression<bool>? isSynced,
    Expression<String>? outletId,
    Expression<String>? ingredientId,
    Expression<double>? computedStock,
    Expression<double>? minStockBase,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (rowVersion != null) 'row_version': rowVersion,
      if (isDeleted != null) 'is_deleted': isDeleted,
      if (lastModifiedHlc != null) 'last_modified_hlc': lastModifiedHlc,
      if (isSynced != null) 'is_synced': isSynced,
      if (outletId != null) 'outlet_id': outletId,
      if (ingredientId != null) 'ingredient_id': ingredientId,
      if (computedStock != null) 'computed_stock': computedStock,
      if (minStockBase != null) 'min_stock_base': minStockBase,
      if (rowid != null) 'rowid': rowid,
    });
  }

  OutletStocksCompanion copyWith(
      {Value<String>? id,
      Value<int>? rowVersion,
      Value<bool>? isDeleted,
      Value<String?>? lastModifiedHlc,
      Value<bool>? isSynced,
      Value<String>? outletId,
      Value<String>? ingredientId,
      Value<double>? computedStock,
      Value<double>? minStockBase,
      Value<int>? rowid}) {
    return OutletStocksCompanion(
      id: id ?? this.id,
      rowVersion: rowVersion ?? this.rowVersion,
      isDeleted: isDeleted ?? this.isDeleted,
      lastModifiedHlc: lastModifiedHlc ?? this.lastModifiedHlc,
      isSynced: isSynced ?? this.isSynced,
      outletId: outletId ?? this.outletId,
      ingredientId: ingredientId ?? this.ingredientId,
      computedStock: computedStock ?? this.computedStock,
      minStockBase: minStockBase ?? this.minStockBase,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (rowVersion.present) {
      map['row_version'] = Variable<int>(rowVersion.value);
    }
    if (isDeleted.present) {
      map['is_deleted'] = Variable<bool>(isDeleted.value);
    }
    if (lastModifiedHlc.present) {
      map['last_modified_hlc'] = Variable<String>(lastModifiedHlc.value);
    }
    if (isSynced.present) {
      map['is_synced'] = Variable<bool>(isSynced.value);
    }
    if (outletId.present) {
      map['outlet_id'] = Variable<String>(outletId.value);
    }
    if (ingredientId.present) {
      map['ingredient_id'] = Variable<String>(ingredientId.value);
    }
    if (computedStock.present) {
      map['computed_stock'] = Variable<double>(computedStock.value);
    }
    if (minStockBase.present) {
      map['min_stock_base'] = Variable<double>(minStockBase.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('OutletStocksCompanion(')
          ..write('id: $id, ')
          ..write('rowVersion: $rowVersion, ')
          ..write('isDeleted: $isDeleted, ')
          ..write('lastModifiedHlc: $lastModifiedHlc, ')
          ..write('isSynced: $isSynced, ')
          ..write('outletId: $outletId, ')
          ..write('ingredientId: $ingredientId, ')
          ..write('computedStock: $computedStock, ')
          ..write('minStockBase: $minStockBase, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDatabase extends GeneratedDatabase {
  _$AppDatabase(QueryExecutor e) : super(e);
  $AppDatabaseManager get managers => $AppDatabaseManager(this);
  late final $ProductsTable products = $ProductsTable(this);
  late final $OrdersTable orders = $OrdersTable(this);
  late final $OrderItemsTable orderItems = $OrderItemsTable(this);
  late final $PaymentsTable payments = $PaymentsTable(this);
  late final $ShiftsTable shifts = $ShiftsTable(this);
  late final $CashActivitiesTable cashActivities = $CashActivitiesTable(this);
  late final $IngredientsTable ingredients = $IngredientsTable(this);
  late final $RecipesTable recipes = $RecipesTable(this);
  late final $RecipeIngredientsTable recipeIngredients =
      $RecipeIngredientsTable(this);
  late final $OutletStocksTable outletStocks = $OutletStocksTable(this);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
        products,
        orders,
        orderItems,
        payments,
        shifts,
        cashActivities,
        ingredients,
        recipes,
        recipeIngredients,
        outletStocks
      ];
}

typedef $$ProductsTableCreateCompanionBuilder = ProductsCompanion Function({
  required String id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  required String brandId,
  Value<String?> categoryId,
  required String name,
  Value<String?> description,
  required double basePrice,
  Value<double?> buyPrice,
  Value<String?> sku,
  Value<String?> barcode,
  Value<String?> imageUrl,
  Value<bool> stockEnabled,
  Value<String> crdtPositive,
  Value<String> crdtNegative,
  Value<double> stockQty,
  Value<bool> isActive,
  Value<int> rowid,
});
typedef $$ProductsTableUpdateCompanionBuilder = ProductsCompanion Function({
  Value<String> id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  Value<String> brandId,
  Value<String?> categoryId,
  Value<String> name,
  Value<String?> description,
  Value<double> basePrice,
  Value<double?> buyPrice,
  Value<String?> sku,
  Value<String?> barcode,
  Value<String?> imageUrl,
  Value<bool> stockEnabled,
  Value<String> crdtPositive,
  Value<String> crdtNegative,
  Value<double> stockQty,
  Value<bool> isActive,
  Value<int> rowid,
});

class $$ProductsTableFilterComposer
    extends Composer<_$AppDatabase, $ProductsTable> {
  $$ProductsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get brandId => $composableBuilder(
      column: $table.brandId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get categoryId => $composableBuilder(
      column: $table.categoryId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get name => $composableBuilder(
      column: $table.name, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get basePrice => $composableBuilder(
      column: $table.basePrice, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get buyPrice => $composableBuilder(
      column: $table.buyPrice, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get sku => $composableBuilder(
      column: $table.sku, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get barcode => $composableBuilder(
      column: $table.barcode, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get imageUrl => $composableBuilder(
      column: $table.imageUrl, builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get stockEnabled => $composableBuilder(
      column: $table.stockEnabled, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get crdtPositive => $composableBuilder(
      column: $table.crdtPositive, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get crdtNegative => $composableBuilder(
      column: $table.crdtNegative, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get stockQty => $composableBuilder(
      column: $table.stockQty, builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isActive => $composableBuilder(
      column: $table.isActive, builder: (column) => ColumnFilters(column));
}

class $$ProductsTableOrderingComposer
    extends Composer<_$AppDatabase, $ProductsTable> {
  $$ProductsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get brandId => $composableBuilder(
      column: $table.brandId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get categoryId => $composableBuilder(
      column: $table.categoryId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get name => $composableBuilder(
      column: $table.name, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get basePrice => $composableBuilder(
      column: $table.basePrice, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get buyPrice => $composableBuilder(
      column: $table.buyPrice, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get sku => $composableBuilder(
      column: $table.sku, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get barcode => $composableBuilder(
      column: $table.barcode, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get imageUrl => $composableBuilder(
      column: $table.imageUrl, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get stockEnabled => $composableBuilder(
      column: $table.stockEnabled,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get crdtPositive => $composableBuilder(
      column: $table.crdtPositive,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get crdtNegative => $composableBuilder(
      column: $table.crdtNegative,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get stockQty => $composableBuilder(
      column: $table.stockQty, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isActive => $composableBuilder(
      column: $table.isActive, builder: (column) => ColumnOrderings(column));
}

class $$ProductsTableAnnotationComposer
    extends Composer<_$AppDatabase, $ProductsTable> {
  $$ProductsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => column);

  GeneratedColumn<bool> get isDeleted =>
      $composableBuilder(column: $table.isDeleted, builder: (column) => column);

  GeneratedColumn<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc, builder: (column) => column);

  GeneratedColumn<bool> get isSynced =>
      $composableBuilder(column: $table.isSynced, builder: (column) => column);

  GeneratedColumn<String> get brandId =>
      $composableBuilder(column: $table.brandId, builder: (column) => column);

  GeneratedColumn<String> get categoryId => $composableBuilder(
      column: $table.categoryId, builder: (column) => column);

  GeneratedColumn<String> get name =>
      $composableBuilder(column: $table.name, builder: (column) => column);

  GeneratedColumn<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => column);

  GeneratedColumn<double> get basePrice =>
      $composableBuilder(column: $table.basePrice, builder: (column) => column);

  GeneratedColumn<double> get buyPrice =>
      $composableBuilder(column: $table.buyPrice, builder: (column) => column);

  GeneratedColumn<String> get sku =>
      $composableBuilder(column: $table.sku, builder: (column) => column);

  GeneratedColumn<String> get barcode =>
      $composableBuilder(column: $table.barcode, builder: (column) => column);

  GeneratedColumn<String> get imageUrl =>
      $composableBuilder(column: $table.imageUrl, builder: (column) => column);

  GeneratedColumn<bool> get stockEnabled => $composableBuilder(
      column: $table.stockEnabled, builder: (column) => column);

  GeneratedColumn<String> get crdtPositive => $composableBuilder(
      column: $table.crdtPositive, builder: (column) => column);

  GeneratedColumn<String> get crdtNegative => $composableBuilder(
      column: $table.crdtNegative, builder: (column) => column);

  GeneratedColumn<double> get stockQty =>
      $composableBuilder(column: $table.stockQty, builder: (column) => column);

  GeneratedColumn<bool> get isActive =>
      $composableBuilder(column: $table.isActive, builder: (column) => column);
}

class $$ProductsTableTableManager extends RootTableManager<
    _$AppDatabase,
    $ProductsTable,
    ProductLocal,
    $$ProductsTableFilterComposer,
    $$ProductsTableOrderingComposer,
    $$ProductsTableAnnotationComposer,
    $$ProductsTableCreateCompanionBuilder,
    $$ProductsTableUpdateCompanionBuilder,
    (ProductLocal, BaseReferences<_$AppDatabase, $ProductsTable, ProductLocal>),
    ProductLocal,
    PrefetchHooks Function()> {
  $$ProductsTableTableManager(_$AppDatabase db, $ProductsTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$ProductsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$ProductsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$ProductsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<String> id = const Value.absent(),
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            Value<String> brandId = const Value.absent(),
            Value<String?> categoryId = const Value.absent(),
            Value<String> name = const Value.absent(),
            Value<String?> description = const Value.absent(),
            Value<double> basePrice = const Value.absent(),
            Value<double?> buyPrice = const Value.absent(),
            Value<String?> sku = const Value.absent(),
            Value<String?> barcode = const Value.absent(),
            Value<String?> imageUrl = const Value.absent(),
            Value<bool> stockEnabled = const Value.absent(),
            Value<String> crdtPositive = const Value.absent(),
            Value<String> crdtNegative = const Value.absent(),
            Value<double> stockQty = const Value.absent(),
            Value<bool> isActive = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              ProductsCompanion(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            brandId: brandId,
            categoryId: categoryId,
            name: name,
            description: description,
            basePrice: basePrice,
            buyPrice: buyPrice,
            sku: sku,
            barcode: barcode,
            imageUrl: imageUrl,
            stockEnabled: stockEnabled,
            crdtPositive: crdtPositive,
            crdtNegative: crdtNegative,
            stockQty: stockQty,
            isActive: isActive,
            rowid: rowid,
          ),
          createCompanionCallback: ({
            required String id,
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            required String brandId,
            Value<String?> categoryId = const Value.absent(),
            required String name,
            Value<String?> description = const Value.absent(),
            required double basePrice,
            Value<double?> buyPrice = const Value.absent(),
            Value<String?> sku = const Value.absent(),
            Value<String?> barcode = const Value.absent(),
            Value<String?> imageUrl = const Value.absent(),
            Value<bool> stockEnabled = const Value.absent(),
            Value<String> crdtPositive = const Value.absent(),
            Value<String> crdtNegative = const Value.absent(),
            Value<double> stockQty = const Value.absent(),
            Value<bool> isActive = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              ProductsCompanion.insert(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            brandId: brandId,
            categoryId: categoryId,
            name: name,
            description: description,
            basePrice: basePrice,
            buyPrice: buyPrice,
            sku: sku,
            barcode: barcode,
            imageUrl: imageUrl,
            stockEnabled: stockEnabled,
            crdtPositive: crdtPositive,
            crdtNegative: crdtNegative,
            stockQty: stockQty,
            isActive: isActive,
            rowid: rowid,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$ProductsTableProcessedTableManager = ProcessedTableManager<
    _$AppDatabase,
    $ProductsTable,
    ProductLocal,
    $$ProductsTableFilterComposer,
    $$ProductsTableOrderingComposer,
    $$ProductsTableAnnotationComposer,
    $$ProductsTableCreateCompanionBuilder,
    $$ProductsTableUpdateCompanionBuilder,
    (ProductLocal, BaseReferences<_$AppDatabase, $ProductsTable, ProductLocal>),
    ProductLocal,
    PrefetchHooks Function()>;
typedef $$OrdersTableCreateCompanionBuilder = OrdersCompanion Function({
  required String id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  required String outletId,
  Value<String?> shiftSessionId,
  Value<String?> customerId,
  Value<String?> tableId,
  Value<String?> userId,
  required String orderNumber,
  required int displayNumber,
  Value<String> status,
  Value<String> orderType,
  Value<double> subtotal,
  Value<double> serviceChargeAmount,
  Value<double> taxAmount,
  Value<double> discountAmount,
  Value<double> totalAmount,
  Value<String?> notes,
  Value<DateTime?> createdAt,
  Value<DateTime?> updatedAt,
  Value<int> rowid,
});
typedef $$OrdersTableUpdateCompanionBuilder = OrdersCompanion Function({
  Value<String> id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  Value<String> outletId,
  Value<String?> shiftSessionId,
  Value<String?> customerId,
  Value<String?> tableId,
  Value<String?> userId,
  Value<String> orderNumber,
  Value<int> displayNumber,
  Value<String> status,
  Value<String> orderType,
  Value<double> subtotal,
  Value<double> serviceChargeAmount,
  Value<double> taxAmount,
  Value<double> discountAmount,
  Value<double> totalAmount,
  Value<String?> notes,
  Value<DateTime?> createdAt,
  Value<DateTime?> updatedAt,
  Value<int> rowid,
});

class $$OrdersTableFilterComposer
    extends Composer<_$AppDatabase, $OrdersTable> {
  $$OrdersTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get outletId => $composableBuilder(
      column: $table.outletId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get shiftSessionId => $composableBuilder(
      column: $table.shiftSessionId,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get customerId => $composableBuilder(
      column: $table.customerId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get tableId => $composableBuilder(
      column: $table.tableId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get userId => $composableBuilder(
      column: $table.userId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get orderNumber => $composableBuilder(
      column: $table.orderNumber, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get displayNumber => $composableBuilder(
      column: $table.displayNumber, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get status => $composableBuilder(
      column: $table.status, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get orderType => $composableBuilder(
      column: $table.orderType, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get subtotal => $composableBuilder(
      column: $table.subtotal, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get serviceChargeAmount => $composableBuilder(
      column: $table.serviceChargeAmount,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get taxAmount => $composableBuilder(
      column: $table.taxAmount, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get discountAmount => $composableBuilder(
      column: $table.discountAmount,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get totalAmount => $composableBuilder(
      column: $table.totalAmount, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get notes => $composableBuilder(
      column: $table.notes, builder: (column) => ColumnFilters(column));

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnFilters(column));

  ColumnFilters<DateTime> get updatedAt => $composableBuilder(
      column: $table.updatedAt, builder: (column) => ColumnFilters(column));
}

class $$OrdersTableOrderingComposer
    extends Composer<_$AppDatabase, $OrdersTable> {
  $$OrdersTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get outletId => $composableBuilder(
      column: $table.outletId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get shiftSessionId => $composableBuilder(
      column: $table.shiftSessionId,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get customerId => $composableBuilder(
      column: $table.customerId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get tableId => $composableBuilder(
      column: $table.tableId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get userId => $composableBuilder(
      column: $table.userId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get orderNumber => $composableBuilder(
      column: $table.orderNumber, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get displayNumber => $composableBuilder(
      column: $table.displayNumber,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get status => $composableBuilder(
      column: $table.status, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get orderType => $composableBuilder(
      column: $table.orderType, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get subtotal => $composableBuilder(
      column: $table.subtotal, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get serviceChargeAmount => $composableBuilder(
      column: $table.serviceChargeAmount,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get taxAmount => $composableBuilder(
      column: $table.taxAmount, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get discountAmount => $composableBuilder(
      column: $table.discountAmount,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get totalAmount => $composableBuilder(
      column: $table.totalAmount, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get notes => $composableBuilder(
      column: $table.notes, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<DateTime> get updatedAt => $composableBuilder(
      column: $table.updatedAt, builder: (column) => ColumnOrderings(column));
}

class $$OrdersTableAnnotationComposer
    extends Composer<_$AppDatabase, $OrdersTable> {
  $$OrdersTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => column);

  GeneratedColumn<bool> get isDeleted =>
      $composableBuilder(column: $table.isDeleted, builder: (column) => column);

  GeneratedColumn<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc, builder: (column) => column);

  GeneratedColumn<bool> get isSynced =>
      $composableBuilder(column: $table.isSynced, builder: (column) => column);

  GeneratedColumn<String> get outletId =>
      $composableBuilder(column: $table.outletId, builder: (column) => column);

  GeneratedColumn<String> get shiftSessionId => $composableBuilder(
      column: $table.shiftSessionId, builder: (column) => column);

  GeneratedColumn<String> get customerId => $composableBuilder(
      column: $table.customerId, builder: (column) => column);

  GeneratedColumn<String> get tableId =>
      $composableBuilder(column: $table.tableId, builder: (column) => column);

  GeneratedColumn<String> get userId =>
      $composableBuilder(column: $table.userId, builder: (column) => column);

  GeneratedColumn<String> get orderNumber => $composableBuilder(
      column: $table.orderNumber, builder: (column) => column);

  GeneratedColumn<int> get displayNumber => $composableBuilder(
      column: $table.displayNumber, builder: (column) => column);

  GeneratedColumn<String> get status =>
      $composableBuilder(column: $table.status, builder: (column) => column);

  GeneratedColumn<String> get orderType =>
      $composableBuilder(column: $table.orderType, builder: (column) => column);

  GeneratedColumn<double> get subtotal =>
      $composableBuilder(column: $table.subtotal, builder: (column) => column);

  GeneratedColumn<double> get serviceChargeAmount => $composableBuilder(
      column: $table.serviceChargeAmount, builder: (column) => column);

  GeneratedColumn<double> get taxAmount =>
      $composableBuilder(column: $table.taxAmount, builder: (column) => column);

  GeneratedColumn<double> get discountAmount => $composableBuilder(
      column: $table.discountAmount, builder: (column) => column);

  GeneratedColumn<double> get totalAmount => $composableBuilder(
      column: $table.totalAmount, builder: (column) => column);

  GeneratedColumn<String> get notes =>
      $composableBuilder(column: $table.notes, builder: (column) => column);

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<DateTime> get updatedAt =>
      $composableBuilder(column: $table.updatedAt, builder: (column) => column);
}

class $$OrdersTableTableManager extends RootTableManager<
    _$AppDatabase,
    $OrdersTable,
    OrderLocal,
    $$OrdersTableFilterComposer,
    $$OrdersTableOrderingComposer,
    $$OrdersTableAnnotationComposer,
    $$OrdersTableCreateCompanionBuilder,
    $$OrdersTableUpdateCompanionBuilder,
    (OrderLocal, BaseReferences<_$AppDatabase, $OrdersTable, OrderLocal>),
    OrderLocal,
    PrefetchHooks Function()> {
  $$OrdersTableTableManager(_$AppDatabase db, $OrdersTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$OrdersTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$OrdersTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$OrdersTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<String> id = const Value.absent(),
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            Value<String> outletId = const Value.absent(),
            Value<String?> shiftSessionId = const Value.absent(),
            Value<String?> customerId = const Value.absent(),
            Value<String?> tableId = const Value.absent(),
            Value<String?> userId = const Value.absent(),
            Value<String> orderNumber = const Value.absent(),
            Value<int> displayNumber = const Value.absent(),
            Value<String> status = const Value.absent(),
            Value<String> orderType = const Value.absent(),
            Value<double> subtotal = const Value.absent(),
            Value<double> serviceChargeAmount = const Value.absent(),
            Value<double> taxAmount = const Value.absent(),
            Value<double> discountAmount = const Value.absent(),
            Value<double> totalAmount = const Value.absent(),
            Value<String?> notes = const Value.absent(),
            Value<DateTime?> createdAt = const Value.absent(),
            Value<DateTime?> updatedAt = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              OrdersCompanion(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            outletId: outletId,
            shiftSessionId: shiftSessionId,
            customerId: customerId,
            tableId: tableId,
            userId: userId,
            orderNumber: orderNumber,
            displayNumber: displayNumber,
            status: status,
            orderType: orderType,
            subtotal: subtotal,
            serviceChargeAmount: serviceChargeAmount,
            taxAmount: taxAmount,
            discountAmount: discountAmount,
            totalAmount: totalAmount,
            notes: notes,
            createdAt: createdAt,
            updatedAt: updatedAt,
            rowid: rowid,
          ),
          createCompanionCallback: ({
            required String id,
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            required String outletId,
            Value<String?> shiftSessionId = const Value.absent(),
            Value<String?> customerId = const Value.absent(),
            Value<String?> tableId = const Value.absent(),
            Value<String?> userId = const Value.absent(),
            required String orderNumber,
            required int displayNumber,
            Value<String> status = const Value.absent(),
            Value<String> orderType = const Value.absent(),
            Value<double> subtotal = const Value.absent(),
            Value<double> serviceChargeAmount = const Value.absent(),
            Value<double> taxAmount = const Value.absent(),
            Value<double> discountAmount = const Value.absent(),
            Value<double> totalAmount = const Value.absent(),
            Value<String?> notes = const Value.absent(),
            Value<DateTime?> createdAt = const Value.absent(),
            Value<DateTime?> updatedAt = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              OrdersCompanion.insert(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            outletId: outletId,
            shiftSessionId: shiftSessionId,
            customerId: customerId,
            tableId: tableId,
            userId: userId,
            orderNumber: orderNumber,
            displayNumber: displayNumber,
            status: status,
            orderType: orderType,
            subtotal: subtotal,
            serviceChargeAmount: serviceChargeAmount,
            taxAmount: taxAmount,
            discountAmount: discountAmount,
            totalAmount: totalAmount,
            notes: notes,
            createdAt: createdAt,
            updatedAt: updatedAt,
            rowid: rowid,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$OrdersTableProcessedTableManager = ProcessedTableManager<
    _$AppDatabase,
    $OrdersTable,
    OrderLocal,
    $$OrdersTableFilterComposer,
    $$OrdersTableOrderingComposer,
    $$OrdersTableAnnotationComposer,
    $$OrdersTableCreateCompanionBuilder,
    $$OrdersTableUpdateCompanionBuilder,
    (OrderLocal, BaseReferences<_$AppDatabase, $OrdersTable, OrderLocal>),
    OrderLocal,
    PrefetchHooks Function()>;
typedef $$OrderItemsTableCreateCompanionBuilder = OrderItemsCompanion Function({
  required String id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  required String orderId,
  required String productId,
  Value<String?> productVariantId,
  required int quantity,
  required double unitPrice,
  Value<double> discountAmount,
  required double totalPrice,
  Value<String?> modifiers,
  Value<String?> notes,
  Value<DateTime?> paidAt,
  Value<String?> paidPaymentId,
  Value<int> rowid,
});
typedef $$OrderItemsTableUpdateCompanionBuilder = OrderItemsCompanion Function({
  Value<String> id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  Value<String> orderId,
  Value<String> productId,
  Value<String?> productVariantId,
  Value<int> quantity,
  Value<double> unitPrice,
  Value<double> discountAmount,
  Value<double> totalPrice,
  Value<String?> modifiers,
  Value<String?> notes,
  Value<DateTime?> paidAt,
  Value<String?> paidPaymentId,
  Value<int> rowid,
});

class $$OrderItemsTableFilterComposer
    extends Composer<_$AppDatabase, $OrderItemsTable> {
  $$OrderItemsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get orderId => $composableBuilder(
      column: $table.orderId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get productId => $composableBuilder(
      column: $table.productId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get productVariantId => $composableBuilder(
      column: $table.productVariantId,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get quantity => $composableBuilder(
      column: $table.quantity, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get unitPrice => $composableBuilder(
      column: $table.unitPrice, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get discountAmount => $composableBuilder(
      column: $table.discountAmount,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get totalPrice => $composableBuilder(
      column: $table.totalPrice, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get modifiers => $composableBuilder(
      column: $table.modifiers, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get notes => $composableBuilder(
      column: $table.notes, builder: (column) => ColumnFilters(column));

  ColumnFilters<DateTime> get paidAt => $composableBuilder(
      column: $table.paidAt, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get paidPaymentId => $composableBuilder(
      column: $table.paidPaymentId, builder: (column) => ColumnFilters(column));
}

class $$OrderItemsTableOrderingComposer
    extends Composer<_$AppDatabase, $OrderItemsTable> {
  $$OrderItemsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get orderId => $composableBuilder(
      column: $table.orderId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get productId => $composableBuilder(
      column: $table.productId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get productVariantId => $composableBuilder(
      column: $table.productVariantId,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get quantity => $composableBuilder(
      column: $table.quantity, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get unitPrice => $composableBuilder(
      column: $table.unitPrice, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get discountAmount => $composableBuilder(
      column: $table.discountAmount,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get totalPrice => $composableBuilder(
      column: $table.totalPrice, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get modifiers => $composableBuilder(
      column: $table.modifiers, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get notes => $composableBuilder(
      column: $table.notes, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<DateTime> get paidAt => $composableBuilder(
      column: $table.paidAt, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get paidPaymentId => $composableBuilder(
      column: $table.paidPaymentId,
      builder: (column) => ColumnOrderings(column));
}

class $$OrderItemsTableAnnotationComposer
    extends Composer<_$AppDatabase, $OrderItemsTable> {
  $$OrderItemsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => column);

  GeneratedColumn<bool> get isDeleted =>
      $composableBuilder(column: $table.isDeleted, builder: (column) => column);

  GeneratedColumn<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc, builder: (column) => column);

  GeneratedColumn<bool> get isSynced =>
      $composableBuilder(column: $table.isSynced, builder: (column) => column);

  GeneratedColumn<String> get orderId =>
      $composableBuilder(column: $table.orderId, builder: (column) => column);

  GeneratedColumn<String> get productId =>
      $composableBuilder(column: $table.productId, builder: (column) => column);

  GeneratedColumn<String> get productVariantId => $composableBuilder(
      column: $table.productVariantId, builder: (column) => column);

  GeneratedColumn<int> get quantity =>
      $composableBuilder(column: $table.quantity, builder: (column) => column);

  GeneratedColumn<double> get unitPrice =>
      $composableBuilder(column: $table.unitPrice, builder: (column) => column);

  GeneratedColumn<double> get discountAmount => $composableBuilder(
      column: $table.discountAmount, builder: (column) => column);

  GeneratedColumn<double> get totalPrice => $composableBuilder(
      column: $table.totalPrice, builder: (column) => column);

  GeneratedColumn<String> get modifiers =>
      $composableBuilder(column: $table.modifiers, builder: (column) => column);

  GeneratedColumn<String> get notes =>
      $composableBuilder(column: $table.notes, builder: (column) => column);

  GeneratedColumn<DateTime> get paidAt =>
      $composableBuilder(column: $table.paidAt, builder: (column) => column);

  GeneratedColumn<String> get paidPaymentId => $composableBuilder(
      column: $table.paidPaymentId, builder: (column) => column);
}

class $$OrderItemsTableTableManager extends RootTableManager<
    _$AppDatabase,
    $OrderItemsTable,
    OrderItemLocal,
    $$OrderItemsTableFilterComposer,
    $$OrderItemsTableOrderingComposer,
    $$OrderItemsTableAnnotationComposer,
    $$OrderItemsTableCreateCompanionBuilder,
    $$OrderItemsTableUpdateCompanionBuilder,
    (
      OrderItemLocal,
      BaseReferences<_$AppDatabase, $OrderItemsTable, OrderItemLocal>
    ),
    OrderItemLocal,
    PrefetchHooks Function()> {
  $$OrderItemsTableTableManager(_$AppDatabase db, $OrderItemsTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$OrderItemsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$OrderItemsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$OrderItemsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<String> id = const Value.absent(),
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            Value<String> orderId = const Value.absent(),
            Value<String> productId = const Value.absent(),
            Value<String?> productVariantId = const Value.absent(),
            Value<int> quantity = const Value.absent(),
            Value<double> unitPrice = const Value.absent(),
            Value<double> discountAmount = const Value.absent(),
            Value<double> totalPrice = const Value.absent(),
            Value<String?> modifiers = const Value.absent(),
            Value<String?> notes = const Value.absent(),
            Value<DateTime?> paidAt = const Value.absent(),
            Value<String?> paidPaymentId = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              OrderItemsCompanion(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            orderId: orderId,
            productId: productId,
            productVariantId: productVariantId,
            quantity: quantity,
            unitPrice: unitPrice,
            discountAmount: discountAmount,
            totalPrice: totalPrice,
            modifiers: modifiers,
            notes: notes,
            paidAt: paidAt,
            paidPaymentId: paidPaymentId,
            rowid: rowid,
          ),
          createCompanionCallback: ({
            required String id,
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            required String orderId,
            required String productId,
            Value<String?> productVariantId = const Value.absent(),
            required int quantity,
            required double unitPrice,
            Value<double> discountAmount = const Value.absent(),
            required double totalPrice,
            Value<String?> modifiers = const Value.absent(),
            Value<String?> notes = const Value.absent(),
            Value<DateTime?> paidAt = const Value.absent(),
            Value<String?> paidPaymentId = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              OrderItemsCompanion.insert(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            orderId: orderId,
            productId: productId,
            productVariantId: productVariantId,
            quantity: quantity,
            unitPrice: unitPrice,
            discountAmount: discountAmount,
            totalPrice: totalPrice,
            modifiers: modifiers,
            notes: notes,
            paidAt: paidAt,
            paidPaymentId: paidPaymentId,
            rowid: rowid,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$OrderItemsTableProcessedTableManager = ProcessedTableManager<
    _$AppDatabase,
    $OrderItemsTable,
    OrderItemLocal,
    $$OrderItemsTableFilterComposer,
    $$OrderItemsTableOrderingComposer,
    $$OrderItemsTableAnnotationComposer,
    $$OrderItemsTableCreateCompanionBuilder,
    $$OrderItemsTableUpdateCompanionBuilder,
    (
      OrderItemLocal,
      BaseReferences<_$AppDatabase, $OrderItemsTable, OrderItemLocal>
    ),
    OrderItemLocal,
    PrefetchHooks Function()>;
typedef $$PaymentsTableCreateCompanionBuilder = PaymentsCompanion Function({
  required String id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  required String orderId,
  required String outletId,
  Value<String?> shiftSessionId,
  required double amountDue,
  required double amountPaid,
  required String paymentMethod,
  Value<String> status,
  Value<String?> referenceNumber,
  Value<DateTime?> paidAt,
  Value<int> rowid,
});
typedef $$PaymentsTableUpdateCompanionBuilder = PaymentsCompanion Function({
  Value<String> id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  Value<String> orderId,
  Value<String> outletId,
  Value<String?> shiftSessionId,
  Value<double> amountDue,
  Value<double> amountPaid,
  Value<String> paymentMethod,
  Value<String> status,
  Value<String?> referenceNumber,
  Value<DateTime?> paidAt,
  Value<int> rowid,
});

class $$PaymentsTableFilterComposer
    extends Composer<_$AppDatabase, $PaymentsTable> {
  $$PaymentsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get orderId => $composableBuilder(
      column: $table.orderId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get outletId => $composableBuilder(
      column: $table.outletId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get shiftSessionId => $composableBuilder(
      column: $table.shiftSessionId,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get amountDue => $composableBuilder(
      column: $table.amountDue, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get amountPaid => $composableBuilder(
      column: $table.amountPaid, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get paymentMethod => $composableBuilder(
      column: $table.paymentMethod, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get status => $composableBuilder(
      column: $table.status, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get referenceNumber => $composableBuilder(
      column: $table.referenceNumber,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<DateTime> get paidAt => $composableBuilder(
      column: $table.paidAt, builder: (column) => ColumnFilters(column));
}

class $$PaymentsTableOrderingComposer
    extends Composer<_$AppDatabase, $PaymentsTable> {
  $$PaymentsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get orderId => $composableBuilder(
      column: $table.orderId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get outletId => $composableBuilder(
      column: $table.outletId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get shiftSessionId => $composableBuilder(
      column: $table.shiftSessionId,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get amountDue => $composableBuilder(
      column: $table.amountDue, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get amountPaid => $composableBuilder(
      column: $table.amountPaid, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get paymentMethod => $composableBuilder(
      column: $table.paymentMethod,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get status => $composableBuilder(
      column: $table.status, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get referenceNumber => $composableBuilder(
      column: $table.referenceNumber,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<DateTime> get paidAt => $composableBuilder(
      column: $table.paidAt, builder: (column) => ColumnOrderings(column));
}

class $$PaymentsTableAnnotationComposer
    extends Composer<_$AppDatabase, $PaymentsTable> {
  $$PaymentsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => column);

  GeneratedColumn<bool> get isDeleted =>
      $composableBuilder(column: $table.isDeleted, builder: (column) => column);

  GeneratedColumn<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc, builder: (column) => column);

  GeneratedColumn<bool> get isSynced =>
      $composableBuilder(column: $table.isSynced, builder: (column) => column);

  GeneratedColumn<String> get orderId =>
      $composableBuilder(column: $table.orderId, builder: (column) => column);

  GeneratedColumn<String> get outletId =>
      $composableBuilder(column: $table.outletId, builder: (column) => column);

  GeneratedColumn<String> get shiftSessionId => $composableBuilder(
      column: $table.shiftSessionId, builder: (column) => column);

  GeneratedColumn<double> get amountDue =>
      $composableBuilder(column: $table.amountDue, builder: (column) => column);

  GeneratedColumn<double> get amountPaid => $composableBuilder(
      column: $table.amountPaid, builder: (column) => column);

  GeneratedColumn<String> get paymentMethod => $composableBuilder(
      column: $table.paymentMethod, builder: (column) => column);

  GeneratedColumn<String> get status =>
      $composableBuilder(column: $table.status, builder: (column) => column);

  GeneratedColumn<String> get referenceNumber => $composableBuilder(
      column: $table.referenceNumber, builder: (column) => column);

  GeneratedColumn<DateTime> get paidAt =>
      $composableBuilder(column: $table.paidAt, builder: (column) => column);
}

class $$PaymentsTableTableManager extends RootTableManager<
    _$AppDatabase,
    $PaymentsTable,
    PaymentLocal,
    $$PaymentsTableFilterComposer,
    $$PaymentsTableOrderingComposer,
    $$PaymentsTableAnnotationComposer,
    $$PaymentsTableCreateCompanionBuilder,
    $$PaymentsTableUpdateCompanionBuilder,
    (PaymentLocal, BaseReferences<_$AppDatabase, $PaymentsTable, PaymentLocal>),
    PaymentLocal,
    PrefetchHooks Function()> {
  $$PaymentsTableTableManager(_$AppDatabase db, $PaymentsTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$PaymentsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$PaymentsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$PaymentsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<String> id = const Value.absent(),
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            Value<String> orderId = const Value.absent(),
            Value<String> outletId = const Value.absent(),
            Value<String?> shiftSessionId = const Value.absent(),
            Value<double> amountDue = const Value.absent(),
            Value<double> amountPaid = const Value.absent(),
            Value<String> paymentMethod = const Value.absent(),
            Value<String> status = const Value.absent(),
            Value<String?> referenceNumber = const Value.absent(),
            Value<DateTime?> paidAt = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              PaymentsCompanion(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            orderId: orderId,
            outletId: outletId,
            shiftSessionId: shiftSessionId,
            amountDue: amountDue,
            amountPaid: amountPaid,
            paymentMethod: paymentMethod,
            status: status,
            referenceNumber: referenceNumber,
            paidAt: paidAt,
            rowid: rowid,
          ),
          createCompanionCallback: ({
            required String id,
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            required String orderId,
            required String outletId,
            Value<String?> shiftSessionId = const Value.absent(),
            required double amountDue,
            required double amountPaid,
            required String paymentMethod,
            Value<String> status = const Value.absent(),
            Value<String?> referenceNumber = const Value.absent(),
            Value<DateTime?> paidAt = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              PaymentsCompanion.insert(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            orderId: orderId,
            outletId: outletId,
            shiftSessionId: shiftSessionId,
            amountDue: amountDue,
            amountPaid: amountPaid,
            paymentMethod: paymentMethod,
            status: status,
            referenceNumber: referenceNumber,
            paidAt: paidAt,
            rowid: rowid,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$PaymentsTableProcessedTableManager = ProcessedTableManager<
    _$AppDatabase,
    $PaymentsTable,
    PaymentLocal,
    $$PaymentsTableFilterComposer,
    $$PaymentsTableOrderingComposer,
    $$PaymentsTableAnnotationComposer,
    $$PaymentsTableCreateCompanionBuilder,
    $$PaymentsTableUpdateCompanionBuilder,
    (PaymentLocal, BaseReferences<_$AppDatabase, $PaymentsTable, PaymentLocal>),
    PaymentLocal,
    PrefetchHooks Function()>;
typedef $$ShiftsTableCreateCompanionBuilder = ShiftsCompanion Function({
  required String id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  required String outletId,
  required String userId,
  Value<String> status,
  required DateTime startTime,
  Value<DateTime?> endTime,
  Value<double> startingCash,
  Value<double?> endingCash,
  Value<double?> expectedEndingCash,
  Value<String?> notes,
  Value<int> rowid,
});
typedef $$ShiftsTableUpdateCompanionBuilder = ShiftsCompanion Function({
  Value<String> id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  Value<String> outletId,
  Value<String> userId,
  Value<String> status,
  Value<DateTime> startTime,
  Value<DateTime?> endTime,
  Value<double> startingCash,
  Value<double?> endingCash,
  Value<double?> expectedEndingCash,
  Value<String?> notes,
  Value<int> rowid,
});

class $$ShiftsTableFilterComposer
    extends Composer<_$AppDatabase, $ShiftsTable> {
  $$ShiftsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get outletId => $composableBuilder(
      column: $table.outletId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get userId => $composableBuilder(
      column: $table.userId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get status => $composableBuilder(
      column: $table.status, builder: (column) => ColumnFilters(column));

  ColumnFilters<DateTime> get startTime => $composableBuilder(
      column: $table.startTime, builder: (column) => ColumnFilters(column));

  ColumnFilters<DateTime> get endTime => $composableBuilder(
      column: $table.endTime, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get startingCash => $composableBuilder(
      column: $table.startingCash, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get endingCash => $composableBuilder(
      column: $table.endingCash, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get expectedEndingCash => $composableBuilder(
      column: $table.expectedEndingCash,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get notes => $composableBuilder(
      column: $table.notes, builder: (column) => ColumnFilters(column));
}

class $$ShiftsTableOrderingComposer
    extends Composer<_$AppDatabase, $ShiftsTable> {
  $$ShiftsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get outletId => $composableBuilder(
      column: $table.outletId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get userId => $composableBuilder(
      column: $table.userId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get status => $composableBuilder(
      column: $table.status, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<DateTime> get startTime => $composableBuilder(
      column: $table.startTime, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<DateTime> get endTime => $composableBuilder(
      column: $table.endTime, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get startingCash => $composableBuilder(
      column: $table.startingCash,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get endingCash => $composableBuilder(
      column: $table.endingCash, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get expectedEndingCash => $composableBuilder(
      column: $table.expectedEndingCash,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get notes => $composableBuilder(
      column: $table.notes, builder: (column) => ColumnOrderings(column));
}

class $$ShiftsTableAnnotationComposer
    extends Composer<_$AppDatabase, $ShiftsTable> {
  $$ShiftsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => column);

  GeneratedColumn<bool> get isDeleted =>
      $composableBuilder(column: $table.isDeleted, builder: (column) => column);

  GeneratedColumn<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc, builder: (column) => column);

  GeneratedColumn<bool> get isSynced =>
      $composableBuilder(column: $table.isSynced, builder: (column) => column);

  GeneratedColumn<String> get outletId =>
      $composableBuilder(column: $table.outletId, builder: (column) => column);

  GeneratedColumn<String> get userId =>
      $composableBuilder(column: $table.userId, builder: (column) => column);

  GeneratedColumn<String> get status =>
      $composableBuilder(column: $table.status, builder: (column) => column);

  GeneratedColumn<DateTime> get startTime =>
      $composableBuilder(column: $table.startTime, builder: (column) => column);

  GeneratedColumn<DateTime> get endTime =>
      $composableBuilder(column: $table.endTime, builder: (column) => column);

  GeneratedColumn<double> get startingCash => $composableBuilder(
      column: $table.startingCash, builder: (column) => column);

  GeneratedColumn<double> get endingCash => $composableBuilder(
      column: $table.endingCash, builder: (column) => column);

  GeneratedColumn<double> get expectedEndingCash => $composableBuilder(
      column: $table.expectedEndingCash, builder: (column) => column);

  GeneratedColumn<String> get notes =>
      $composableBuilder(column: $table.notes, builder: (column) => column);
}

class $$ShiftsTableTableManager extends RootTableManager<
    _$AppDatabase,
    $ShiftsTable,
    ShiftLocal,
    $$ShiftsTableFilterComposer,
    $$ShiftsTableOrderingComposer,
    $$ShiftsTableAnnotationComposer,
    $$ShiftsTableCreateCompanionBuilder,
    $$ShiftsTableUpdateCompanionBuilder,
    (ShiftLocal, BaseReferences<_$AppDatabase, $ShiftsTable, ShiftLocal>),
    ShiftLocal,
    PrefetchHooks Function()> {
  $$ShiftsTableTableManager(_$AppDatabase db, $ShiftsTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$ShiftsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$ShiftsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$ShiftsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<String> id = const Value.absent(),
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            Value<String> outletId = const Value.absent(),
            Value<String> userId = const Value.absent(),
            Value<String> status = const Value.absent(),
            Value<DateTime> startTime = const Value.absent(),
            Value<DateTime?> endTime = const Value.absent(),
            Value<double> startingCash = const Value.absent(),
            Value<double?> endingCash = const Value.absent(),
            Value<double?> expectedEndingCash = const Value.absent(),
            Value<String?> notes = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              ShiftsCompanion(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            outletId: outletId,
            userId: userId,
            status: status,
            startTime: startTime,
            endTime: endTime,
            startingCash: startingCash,
            endingCash: endingCash,
            expectedEndingCash: expectedEndingCash,
            notes: notes,
            rowid: rowid,
          ),
          createCompanionCallback: ({
            required String id,
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            required String outletId,
            required String userId,
            Value<String> status = const Value.absent(),
            required DateTime startTime,
            Value<DateTime?> endTime = const Value.absent(),
            Value<double> startingCash = const Value.absent(),
            Value<double?> endingCash = const Value.absent(),
            Value<double?> expectedEndingCash = const Value.absent(),
            Value<String?> notes = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              ShiftsCompanion.insert(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            outletId: outletId,
            userId: userId,
            status: status,
            startTime: startTime,
            endTime: endTime,
            startingCash: startingCash,
            endingCash: endingCash,
            expectedEndingCash: expectedEndingCash,
            notes: notes,
            rowid: rowid,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$ShiftsTableProcessedTableManager = ProcessedTableManager<
    _$AppDatabase,
    $ShiftsTable,
    ShiftLocal,
    $$ShiftsTableFilterComposer,
    $$ShiftsTableOrderingComposer,
    $$ShiftsTableAnnotationComposer,
    $$ShiftsTableCreateCompanionBuilder,
    $$ShiftsTableUpdateCompanionBuilder,
    (ShiftLocal, BaseReferences<_$AppDatabase, $ShiftsTable, ShiftLocal>),
    ShiftLocal,
    PrefetchHooks Function()>;
typedef $$CashActivitiesTableCreateCompanionBuilder = CashActivitiesCompanion
    Function({
  required String id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  required String shiftId,
  required String activityType,
  required double amount,
  required String description,
  Value<int> rowid,
});
typedef $$CashActivitiesTableUpdateCompanionBuilder = CashActivitiesCompanion
    Function({
  Value<String> id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  Value<String> shiftId,
  Value<String> activityType,
  Value<double> amount,
  Value<String> description,
  Value<int> rowid,
});

class $$CashActivitiesTableFilterComposer
    extends Composer<_$AppDatabase, $CashActivitiesTable> {
  $$CashActivitiesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get shiftId => $composableBuilder(
      column: $table.shiftId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get activityType => $composableBuilder(
      column: $table.activityType, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get amount => $composableBuilder(
      column: $table.amount, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => ColumnFilters(column));
}

class $$CashActivitiesTableOrderingComposer
    extends Composer<_$AppDatabase, $CashActivitiesTable> {
  $$CashActivitiesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get shiftId => $composableBuilder(
      column: $table.shiftId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get activityType => $composableBuilder(
      column: $table.activityType,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get amount => $composableBuilder(
      column: $table.amount, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => ColumnOrderings(column));
}

class $$CashActivitiesTableAnnotationComposer
    extends Composer<_$AppDatabase, $CashActivitiesTable> {
  $$CashActivitiesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => column);

  GeneratedColumn<bool> get isDeleted =>
      $composableBuilder(column: $table.isDeleted, builder: (column) => column);

  GeneratedColumn<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc, builder: (column) => column);

  GeneratedColumn<bool> get isSynced =>
      $composableBuilder(column: $table.isSynced, builder: (column) => column);

  GeneratedColumn<String> get shiftId =>
      $composableBuilder(column: $table.shiftId, builder: (column) => column);

  GeneratedColumn<String> get activityType => $composableBuilder(
      column: $table.activityType, builder: (column) => column);

  GeneratedColumn<double> get amount =>
      $composableBuilder(column: $table.amount, builder: (column) => column);

  GeneratedColumn<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => column);
}

class $$CashActivitiesTableTableManager extends RootTableManager<
    _$AppDatabase,
    $CashActivitiesTable,
    CashActivityLocal,
    $$CashActivitiesTableFilterComposer,
    $$CashActivitiesTableOrderingComposer,
    $$CashActivitiesTableAnnotationComposer,
    $$CashActivitiesTableCreateCompanionBuilder,
    $$CashActivitiesTableUpdateCompanionBuilder,
    (
      CashActivityLocal,
      BaseReferences<_$AppDatabase, $CashActivitiesTable, CashActivityLocal>
    ),
    CashActivityLocal,
    PrefetchHooks Function()> {
  $$CashActivitiesTableTableManager(
      _$AppDatabase db, $CashActivitiesTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$CashActivitiesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$CashActivitiesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$CashActivitiesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<String> id = const Value.absent(),
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            Value<String> shiftId = const Value.absent(),
            Value<String> activityType = const Value.absent(),
            Value<double> amount = const Value.absent(),
            Value<String> description = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              CashActivitiesCompanion(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            shiftId: shiftId,
            activityType: activityType,
            amount: amount,
            description: description,
            rowid: rowid,
          ),
          createCompanionCallback: ({
            required String id,
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            required String shiftId,
            required String activityType,
            required double amount,
            required String description,
            Value<int> rowid = const Value.absent(),
          }) =>
              CashActivitiesCompanion.insert(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            shiftId: shiftId,
            activityType: activityType,
            amount: amount,
            description: description,
            rowid: rowid,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$CashActivitiesTableProcessedTableManager = ProcessedTableManager<
    _$AppDatabase,
    $CashActivitiesTable,
    CashActivityLocal,
    $$CashActivitiesTableFilterComposer,
    $$CashActivitiesTableOrderingComposer,
    $$CashActivitiesTableAnnotationComposer,
    $$CashActivitiesTableCreateCompanionBuilder,
    $$CashActivitiesTableUpdateCompanionBuilder,
    (
      CashActivityLocal,
      BaseReferences<_$AppDatabase, $CashActivitiesTable, CashActivityLocal>
    ),
    CashActivityLocal,
    PrefetchHooks Function()>;
typedef $$IngredientsTableCreateCompanionBuilder = IngredientsCompanion
    Function({
  required String id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  required String brandId,
  required String name,
  required String trackingMode,
  required String baseUnit,
  required String unitType,
  Value<double> buyPrice,
  Value<double> buyQty,
  Value<double> costPerBaseUnit,
  Value<String> ingredientType,
  Value<int> rowid,
});
typedef $$IngredientsTableUpdateCompanionBuilder = IngredientsCompanion
    Function({
  Value<String> id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  Value<String> brandId,
  Value<String> name,
  Value<String> trackingMode,
  Value<String> baseUnit,
  Value<String> unitType,
  Value<double> buyPrice,
  Value<double> buyQty,
  Value<double> costPerBaseUnit,
  Value<String> ingredientType,
  Value<int> rowid,
});

class $$IngredientsTableFilterComposer
    extends Composer<_$AppDatabase, $IngredientsTable> {
  $$IngredientsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get brandId => $composableBuilder(
      column: $table.brandId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get name => $composableBuilder(
      column: $table.name, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get trackingMode => $composableBuilder(
      column: $table.trackingMode, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get baseUnit => $composableBuilder(
      column: $table.baseUnit, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get unitType => $composableBuilder(
      column: $table.unitType, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get buyPrice => $composableBuilder(
      column: $table.buyPrice, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get buyQty => $composableBuilder(
      column: $table.buyQty, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get costPerBaseUnit => $composableBuilder(
      column: $table.costPerBaseUnit,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get ingredientType => $composableBuilder(
      column: $table.ingredientType,
      builder: (column) => ColumnFilters(column));
}

class $$IngredientsTableOrderingComposer
    extends Composer<_$AppDatabase, $IngredientsTable> {
  $$IngredientsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get brandId => $composableBuilder(
      column: $table.brandId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get name => $composableBuilder(
      column: $table.name, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get trackingMode => $composableBuilder(
      column: $table.trackingMode,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get baseUnit => $composableBuilder(
      column: $table.baseUnit, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get unitType => $composableBuilder(
      column: $table.unitType, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get buyPrice => $composableBuilder(
      column: $table.buyPrice, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get buyQty => $composableBuilder(
      column: $table.buyQty, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get costPerBaseUnit => $composableBuilder(
      column: $table.costPerBaseUnit,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get ingredientType => $composableBuilder(
      column: $table.ingredientType,
      builder: (column) => ColumnOrderings(column));
}

class $$IngredientsTableAnnotationComposer
    extends Composer<_$AppDatabase, $IngredientsTable> {
  $$IngredientsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => column);

  GeneratedColumn<bool> get isDeleted =>
      $composableBuilder(column: $table.isDeleted, builder: (column) => column);

  GeneratedColumn<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc, builder: (column) => column);

  GeneratedColumn<bool> get isSynced =>
      $composableBuilder(column: $table.isSynced, builder: (column) => column);

  GeneratedColumn<String> get brandId =>
      $composableBuilder(column: $table.brandId, builder: (column) => column);

  GeneratedColumn<String> get name =>
      $composableBuilder(column: $table.name, builder: (column) => column);

  GeneratedColumn<String> get trackingMode => $composableBuilder(
      column: $table.trackingMode, builder: (column) => column);

  GeneratedColumn<String> get baseUnit =>
      $composableBuilder(column: $table.baseUnit, builder: (column) => column);

  GeneratedColumn<String> get unitType =>
      $composableBuilder(column: $table.unitType, builder: (column) => column);

  GeneratedColumn<double> get buyPrice =>
      $composableBuilder(column: $table.buyPrice, builder: (column) => column);

  GeneratedColumn<double> get buyQty =>
      $composableBuilder(column: $table.buyQty, builder: (column) => column);

  GeneratedColumn<double> get costPerBaseUnit => $composableBuilder(
      column: $table.costPerBaseUnit, builder: (column) => column);

  GeneratedColumn<String> get ingredientType => $composableBuilder(
      column: $table.ingredientType, builder: (column) => column);
}

class $$IngredientsTableTableManager extends RootTableManager<
    _$AppDatabase,
    $IngredientsTable,
    IngredientLocal,
    $$IngredientsTableFilterComposer,
    $$IngredientsTableOrderingComposer,
    $$IngredientsTableAnnotationComposer,
    $$IngredientsTableCreateCompanionBuilder,
    $$IngredientsTableUpdateCompanionBuilder,
    (
      IngredientLocal,
      BaseReferences<_$AppDatabase, $IngredientsTable, IngredientLocal>
    ),
    IngredientLocal,
    PrefetchHooks Function()> {
  $$IngredientsTableTableManager(_$AppDatabase db, $IngredientsTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$IngredientsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$IngredientsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$IngredientsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<String> id = const Value.absent(),
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            Value<String> brandId = const Value.absent(),
            Value<String> name = const Value.absent(),
            Value<String> trackingMode = const Value.absent(),
            Value<String> baseUnit = const Value.absent(),
            Value<String> unitType = const Value.absent(),
            Value<double> buyPrice = const Value.absent(),
            Value<double> buyQty = const Value.absent(),
            Value<double> costPerBaseUnit = const Value.absent(),
            Value<String> ingredientType = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              IngredientsCompanion(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            brandId: brandId,
            name: name,
            trackingMode: trackingMode,
            baseUnit: baseUnit,
            unitType: unitType,
            buyPrice: buyPrice,
            buyQty: buyQty,
            costPerBaseUnit: costPerBaseUnit,
            ingredientType: ingredientType,
            rowid: rowid,
          ),
          createCompanionCallback: ({
            required String id,
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            required String brandId,
            required String name,
            required String trackingMode,
            required String baseUnit,
            required String unitType,
            Value<double> buyPrice = const Value.absent(),
            Value<double> buyQty = const Value.absent(),
            Value<double> costPerBaseUnit = const Value.absent(),
            Value<String> ingredientType = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              IngredientsCompanion.insert(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            brandId: brandId,
            name: name,
            trackingMode: trackingMode,
            baseUnit: baseUnit,
            unitType: unitType,
            buyPrice: buyPrice,
            buyQty: buyQty,
            costPerBaseUnit: costPerBaseUnit,
            ingredientType: ingredientType,
            rowid: rowid,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$IngredientsTableProcessedTableManager = ProcessedTableManager<
    _$AppDatabase,
    $IngredientsTable,
    IngredientLocal,
    $$IngredientsTableFilterComposer,
    $$IngredientsTableOrderingComposer,
    $$IngredientsTableAnnotationComposer,
    $$IngredientsTableCreateCompanionBuilder,
    $$IngredientsTableUpdateCompanionBuilder,
    (
      IngredientLocal,
      BaseReferences<_$AppDatabase, $IngredientsTable, IngredientLocal>
    ),
    IngredientLocal,
    PrefetchHooks Function()>;
typedef $$RecipesTableCreateCompanionBuilder = RecipesCompanion Function({
  required String id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  required String productId,
  Value<int> version,
  Value<bool> isActive,
  Value<String?> notes,
  Value<int> rowid,
});
typedef $$RecipesTableUpdateCompanionBuilder = RecipesCompanion Function({
  Value<String> id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  Value<String> productId,
  Value<int> version,
  Value<bool> isActive,
  Value<String?> notes,
  Value<int> rowid,
});

class $$RecipesTableFilterComposer
    extends Composer<_$AppDatabase, $RecipesTable> {
  $$RecipesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get productId => $composableBuilder(
      column: $table.productId, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get version => $composableBuilder(
      column: $table.version, builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isActive => $composableBuilder(
      column: $table.isActive, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get notes => $composableBuilder(
      column: $table.notes, builder: (column) => ColumnFilters(column));
}

class $$RecipesTableOrderingComposer
    extends Composer<_$AppDatabase, $RecipesTable> {
  $$RecipesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get productId => $composableBuilder(
      column: $table.productId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get version => $composableBuilder(
      column: $table.version, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isActive => $composableBuilder(
      column: $table.isActive, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get notes => $composableBuilder(
      column: $table.notes, builder: (column) => ColumnOrderings(column));
}

class $$RecipesTableAnnotationComposer
    extends Composer<_$AppDatabase, $RecipesTable> {
  $$RecipesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => column);

  GeneratedColumn<bool> get isDeleted =>
      $composableBuilder(column: $table.isDeleted, builder: (column) => column);

  GeneratedColumn<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc, builder: (column) => column);

  GeneratedColumn<bool> get isSynced =>
      $composableBuilder(column: $table.isSynced, builder: (column) => column);

  GeneratedColumn<String> get productId =>
      $composableBuilder(column: $table.productId, builder: (column) => column);

  GeneratedColumn<int> get version =>
      $composableBuilder(column: $table.version, builder: (column) => column);

  GeneratedColumn<bool> get isActive =>
      $composableBuilder(column: $table.isActive, builder: (column) => column);

  GeneratedColumn<String> get notes =>
      $composableBuilder(column: $table.notes, builder: (column) => column);
}

class $$RecipesTableTableManager extends RootTableManager<
    _$AppDatabase,
    $RecipesTable,
    RecipeLocal,
    $$RecipesTableFilterComposer,
    $$RecipesTableOrderingComposer,
    $$RecipesTableAnnotationComposer,
    $$RecipesTableCreateCompanionBuilder,
    $$RecipesTableUpdateCompanionBuilder,
    (RecipeLocal, BaseReferences<_$AppDatabase, $RecipesTable, RecipeLocal>),
    RecipeLocal,
    PrefetchHooks Function()> {
  $$RecipesTableTableManager(_$AppDatabase db, $RecipesTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$RecipesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$RecipesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$RecipesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<String> id = const Value.absent(),
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            Value<String> productId = const Value.absent(),
            Value<int> version = const Value.absent(),
            Value<bool> isActive = const Value.absent(),
            Value<String?> notes = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              RecipesCompanion(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            productId: productId,
            version: version,
            isActive: isActive,
            notes: notes,
            rowid: rowid,
          ),
          createCompanionCallback: ({
            required String id,
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            required String productId,
            Value<int> version = const Value.absent(),
            Value<bool> isActive = const Value.absent(),
            Value<String?> notes = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              RecipesCompanion.insert(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            productId: productId,
            version: version,
            isActive: isActive,
            notes: notes,
            rowid: rowid,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$RecipesTableProcessedTableManager = ProcessedTableManager<
    _$AppDatabase,
    $RecipesTable,
    RecipeLocal,
    $$RecipesTableFilterComposer,
    $$RecipesTableOrderingComposer,
    $$RecipesTableAnnotationComposer,
    $$RecipesTableCreateCompanionBuilder,
    $$RecipesTableUpdateCompanionBuilder,
    (RecipeLocal, BaseReferences<_$AppDatabase, $RecipesTable, RecipeLocal>),
    RecipeLocal,
    PrefetchHooks Function()>;
typedef $$RecipeIngredientsTableCreateCompanionBuilder
    = RecipeIngredientsCompanion Function({
  required String id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  required String recipeId,
  required String ingredientId,
  required double quantity,
  required String quantityUnit,
  Value<String?> notes,
  Value<bool> isOptional,
  Value<int> rowid,
});
typedef $$RecipeIngredientsTableUpdateCompanionBuilder
    = RecipeIngredientsCompanion Function({
  Value<String> id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  Value<String> recipeId,
  Value<String> ingredientId,
  Value<double> quantity,
  Value<String> quantityUnit,
  Value<String?> notes,
  Value<bool> isOptional,
  Value<int> rowid,
});

class $$RecipeIngredientsTableFilterComposer
    extends Composer<_$AppDatabase, $RecipeIngredientsTable> {
  $$RecipeIngredientsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get recipeId => $composableBuilder(
      column: $table.recipeId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get ingredientId => $composableBuilder(
      column: $table.ingredientId, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get quantity => $composableBuilder(
      column: $table.quantity, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get quantityUnit => $composableBuilder(
      column: $table.quantityUnit, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get notes => $composableBuilder(
      column: $table.notes, builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isOptional => $composableBuilder(
      column: $table.isOptional, builder: (column) => ColumnFilters(column));
}

class $$RecipeIngredientsTableOrderingComposer
    extends Composer<_$AppDatabase, $RecipeIngredientsTable> {
  $$RecipeIngredientsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get recipeId => $composableBuilder(
      column: $table.recipeId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get ingredientId => $composableBuilder(
      column: $table.ingredientId,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get quantity => $composableBuilder(
      column: $table.quantity, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get quantityUnit => $composableBuilder(
      column: $table.quantityUnit,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get notes => $composableBuilder(
      column: $table.notes, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isOptional => $composableBuilder(
      column: $table.isOptional, builder: (column) => ColumnOrderings(column));
}

class $$RecipeIngredientsTableAnnotationComposer
    extends Composer<_$AppDatabase, $RecipeIngredientsTable> {
  $$RecipeIngredientsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => column);

  GeneratedColumn<bool> get isDeleted =>
      $composableBuilder(column: $table.isDeleted, builder: (column) => column);

  GeneratedColumn<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc, builder: (column) => column);

  GeneratedColumn<bool> get isSynced =>
      $composableBuilder(column: $table.isSynced, builder: (column) => column);

  GeneratedColumn<String> get recipeId =>
      $composableBuilder(column: $table.recipeId, builder: (column) => column);

  GeneratedColumn<String> get ingredientId => $composableBuilder(
      column: $table.ingredientId, builder: (column) => column);

  GeneratedColumn<double> get quantity =>
      $composableBuilder(column: $table.quantity, builder: (column) => column);

  GeneratedColumn<String> get quantityUnit => $composableBuilder(
      column: $table.quantityUnit, builder: (column) => column);

  GeneratedColumn<String> get notes =>
      $composableBuilder(column: $table.notes, builder: (column) => column);

  GeneratedColumn<bool> get isOptional => $composableBuilder(
      column: $table.isOptional, builder: (column) => column);
}

class $$RecipeIngredientsTableTableManager extends RootTableManager<
    _$AppDatabase,
    $RecipeIngredientsTable,
    RecipeIngredientLocal,
    $$RecipeIngredientsTableFilterComposer,
    $$RecipeIngredientsTableOrderingComposer,
    $$RecipeIngredientsTableAnnotationComposer,
    $$RecipeIngredientsTableCreateCompanionBuilder,
    $$RecipeIngredientsTableUpdateCompanionBuilder,
    (
      RecipeIngredientLocal,
      BaseReferences<_$AppDatabase, $RecipeIngredientsTable,
          RecipeIngredientLocal>
    ),
    RecipeIngredientLocal,
    PrefetchHooks Function()> {
  $$RecipeIngredientsTableTableManager(
      _$AppDatabase db, $RecipeIngredientsTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$RecipeIngredientsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$RecipeIngredientsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$RecipeIngredientsTableAnnotationComposer(
                  $db: db, $table: table),
          updateCompanionCallback: ({
            Value<String> id = const Value.absent(),
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            Value<String> recipeId = const Value.absent(),
            Value<String> ingredientId = const Value.absent(),
            Value<double> quantity = const Value.absent(),
            Value<String> quantityUnit = const Value.absent(),
            Value<String?> notes = const Value.absent(),
            Value<bool> isOptional = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              RecipeIngredientsCompanion(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            recipeId: recipeId,
            ingredientId: ingredientId,
            quantity: quantity,
            quantityUnit: quantityUnit,
            notes: notes,
            isOptional: isOptional,
            rowid: rowid,
          ),
          createCompanionCallback: ({
            required String id,
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            required String recipeId,
            required String ingredientId,
            required double quantity,
            required String quantityUnit,
            Value<String?> notes = const Value.absent(),
            Value<bool> isOptional = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              RecipeIngredientsCompanion.insert(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            recipeId: recipeId,
            ingredientId: ingredientId,
            quantity: quantity,
            quantityUnit: quantityUnit,
            notes: notes,
            isOptional: isOptional,
            rowid: rowid,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$RecipeIngredientsTableProcessedTableManager = ProcessedTableManager<
    _$AppDatabase,
    $RecipeIngredientsTable,
    RecipeIngredientLocal,
    $$RecipeIngredientsTableFilterComposer,
    $$RecipeIngredientsTableOrderingComposer,
    $$RecipeIngredientsTableAnnotationComposer,
    $$RecipeIngredientsTableCreateCompanionBuilder,
    $$RecipeIngredientsTableUpdateCompanionBuilder,
    (
      RecipeIngredientLocal,
      BaseReferences<_$AppDatabase, $RecipeIngredientsTable,
          RecipeIngredientLocal>
    ),
    RecipeIngredientLocal,
    PrefetchHooks Function()>;
typedef $$OutletStocksTableCreateCompanionBuilder = OutletStocksCompanion
    Function({
  required String id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  required String outletId,
  required String ingredientId,
  Value<double> computedStock,
  Value<double> minStockBase,
  Value<int> rowid,
});
typedef $$OutletStocksTableUpdateCompanionBuilder = OutletStocksCompanion
    Function({
  Value<String> id,
  Value<int> rowVersion,
  Value<bool> isDeleted,
  Value<String?> lastModifiedHlc,
  Value<bool> isSynced,
  Value<String> outletId,
  Value<String> ingredientId,
  Value<double> computedStock,
  Value<double> minStockBase,
  Value<int> rowid,
});

class $$OutletStocksTableFilterComposer
    extends Composer<_$AppDatabase, $OutletStocksTable> {
  $$OutletStocksTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get outletId => $composableBuilder(
      column: $table.outletId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get ingredientId => $composableBuilder(
      column: $table.ingredientId, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get computedStock => $composableBuilder(
      column: $table.computedStock, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get minStockBase => $composableBuilder(
      column: $table.minStockBase, builder: (column) => ColumnFilters(column));
}

class $$OutletStocksTableOrderingComposer
    extends Composer<_$AppDatabase, $OutletStocksTable> {
  $$OutletStocksTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isDeleted => $composableBuilder(
      column: $table.isDeleted, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isSynced => $composableBuilder(
      column: $table.isSynced, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get outletId => $composableBuilder(
      column: $table.outletId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get ingredientId => $composableBuilder(
      column: $table.ingredientId,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get computedStock => $composableBuilder(
      column: $table.computedStock,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get minStockBase => $composableBuilder(
      column: $table.minStockBase,
      builder: (column) => ColumnOrderings(column));
}

class $$OutletStocksTableAnnotationComposer
    extends Composer<_$AppDatabase, $OutletStocksTable> {
  $$OutletStocksTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get rowVersion => $composableBuilder(
      column: $table.rowVersion, builder: (column) => column);

  GeneratedColumn<bool> get isDeleted =>
      $composableBuilder(column: $table.isDeleted, builder: (column) => column);

  GeneratedColumn<String> get lastModifiedHlc => $composableBuilder(
      column: $table.lastModifiedHlc, builder: (column) => column);

  GeneratedColumn<bool> get isSynced =>
      $composableBuilder(column: $table.isSynced, builder: (column) => column);

  GeneratedColumn<String> get outletId =>
      $composableBuilder(column: $table.outletId, builder: (column) => column);

  GeneratedColumn<String> get ingredientId => $composableBuilder(
      column: $table.ingredientId, builder: (column) => column);

  GeneratedColumn<double> get computedStock => $composableBuilder(
      column: $table.computedStock, builder: (column) => column);

  GeneratedColumn<double> get minStockBase => $composableBuilder(
      column: $table.minStockBase, builder: (column) => column);
}

class $$OutletStocksTableTableManager extends RootTableManager<
    _$AppDatabase,
    $OutletStocksTable,
    OutletStockLocal,
    $$OutletStocksTableFilterComposer,
    $$OutletStocksTableOrderingComposer,
    $$OutletStocksTableAnnotationComposer,
    $$OutletStocksTableCreateCompanionBuilder,
    $$OutletStocksTableUpdateCompanionBuilder,
    (
      OutletStockLocal,
      BaseReferences<_$AppDatabase, $OutletStocksTable, OutletStockLocal>
    ),
    OutletStockLocal,
    PrefetchHooks Function()> {
  $$OutletStocksTableTableManager(_$AppDatabase db, $OutletStocksTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$OutletStocksTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$OutletStocksTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$OutletStocksTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<String> id = const Value.absent(),
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            Value<String> outletId = const Value.absent(),
            Value<String> ingredientId = const Value.absent(),
            Value<double> computedStock = const Value.absent(),
            Value<double> minStockBase = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              OutletStocksCompanion(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            outletId: outletId,
            ingredientId: ingredientId,
            computedStock: computedStock,
            minStockBase: minStockBase,
            rowid: rowid,
          ),
          createCompanionCallback: ({
            required String id,
            Value<int> rowVersion = const Value.absent(),
            Value<bool> isDeleted = const Value.absent(),
            Value<String?> lastModifiedHlc = const Value.absent(),
            Value<bool> isSynced = const Value.absent(),
            required String outletId,
            required String ingredientId,
            Value<double> computedStock = const Value.absent(),
            Value<double> minStockBase = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              OutletStocksCompanion.insert(
            id: id,
            rowVersion: rowVersion,
            isDeleted: isDeleted,
            lastModifiedHlc: lastModifiedHlc,
            isSynced: isSynced,
            outletId: outletId,
            ingredientId: ingredientId,
            computedStock: computedStock,
            minStockBase: minStockBase,
            rowid: rowid,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$OutletStocksTableProcessedTableManager = ProcessedTableManager<
    _$AppDatabase,
    $OutletStocksTable,
    OutletStockLocal,
    $$OutletStocksTableFilterComposer,
    $$OutletStocksTableOrderingComposer,
    $$OutletStocksTableAnnotationComposer,
    $$OutletStocksTableCreateCompanionBuilder,
    $$OutletStocksTableUpdateCompanionBuilder,
    (
      OutletStockLocal,
      BaseReferences<_$AppDatabase, $OutletStocksTable, OutletStockLocal>
    ),
    OutletStockLocal,
    PrefetchHooks Function()>;

class $AppDatabaseManager {
  final _$AppDatabase _db;
  $AppDatabaseManager(this._db);
  $$ProductsTableTableManager get products =>
      $$ProductsTableTableManager(_db, _db.products);
  $$OrdersTableTableManager get orders =>
      $$OrdersTableTableManager(_db, _db.orders);
  $$OrderItemsTableTableManager get orderItems =>
      $$OrderItemsTableTableManager(_db, _db.orderItems);
  $$PaymentsTableTableManager get payments =>
      $$PaymentsTableTableManager(_db, _db.payments);
  $$ShiftsTableTableManager get shifts =>
      $$ShiftsTableTableManager(_db, _db.shifts);
  $$CashActivitiesTableTableManager get cashActivities =>
      $$CashActivitiesTableTableManager(_db, _db.cashActivities);
  $$IngredientsTableTableManager get ingredients =>
      $$IngredientsTableTableManager(_db, _db.ingredients);
  $$RecipesTableTableManager get recipes =>
      $$RecipesTableTableManager(_db, _db.recipes);
  $$RecipeIngredientsTableTableManager get recipeIngredients =>
      $$RecipeIngredientsTableTableManager(_db, _db.recipeIngredients);
  $$OutletStocksTableTableManager get outletStocks =>
      $$OutletStocksTableTableManager(_db, _db.outletStocks);
}
